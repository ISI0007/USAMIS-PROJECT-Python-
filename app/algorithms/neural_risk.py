"""Layer 3: small dense neural network, independent of Flask and SQL.

Two hidden ReLU layers (32, 16), sigmoid output, binary cross-entropy,
L2 regularisation and validation-based early stopping. NumPy backpropagation
keeps the mathematics inspectable for the academic demonstration.
"""
from __future__ import annotations

import numpy as np

FEATURES = ("prior_average", "attendance_rate", "early_average", "credit_load")
BOUNDS = np.array([[0, 100], [0, 1], [0, 100], [1, 40]], dtype=float)


def validate_features(values):
    x = np.asarray(values, dtype=float)
    if x.ndim == 1:
        x = x.reshape(1, -1)
    if x.ndim != 2 or x.shape[1] != len(FEATURES) or len(x) == 0:
        raise ValueError("Provide four features for at least one observation.")
    if not np.isfinite(x).all():
        raise ValueError("Features must be finite numbers.")
    if ((x < BOUNDS[:, 0]) | (x > BOUNDS[:, 1])).any():
        raise ValueError("Scores must be 0–100, attendance 0–1 and credits 1–40.")
    return x


def metrics(y, probabilities):
    y = np.asarray(y, dtype=int)
    p = np.asarray(probabilities, dtype=float)
    predicted = p >= 0.5
    tp = int(np.sum(predicted & (y == 1)))
    tn = int(np.sum(~predicted & (y == 0)))
    fp = int(np.sum(predicted & (y == 0)))
    fn = int(np.sum(~predicted & (y == 1)))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"accuracy": (tp + tn) / len(y), "precision": precision,
            "recall": recall, "f1": 2 * precision * recall / (precision + recall)
            if precision + recall else 0.0,
            "confusion_matrix": [[tn, fp], [fn, tp]],
            "brier_score": float(np.mean((p - y) ** 2))}


class NeuralRiskModel:
    def __init__(self, hidden=(32, 16), seed=42):
        self.hidden = tuple(hidden)
        self.seed = seed
        self.weights = []
        self.biases = []
        self.mean = None
        self.scale = None
        self.history = []

    def _forward(self, x):
        activations = [x]
        for i, (w, b) in enumerate(zip(self.weights, self.biases)):
            z = activations[-1] @ w + b
            a = np.maximum(z, 0) if i < len(self.weights) - 1 else (
                1 / (1 + np.exp(-np.clip(z, -500, 500))))
            activations.append(a)
        return activations

    @staticmethod
    def _loss(y, p):
        p = np.clip(p, 1e-12, 1 - 1e-12)
        return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))

    def fit(self, x, y, validation_x, validation_y, epochs=1200, patience=80):
        x, vx = validate_features(x), validate_features(validation_x)
        y, vy = np.asarray(y, dtype=float).reshape(-1, 1), np.asarray(validation_y, dtype=float).reshape(-1, 1)
        if len(x) != len(y) or len(vx) != len(vy):
            raise ValueError("Feature and outcome counts differ.")
        if set(np.unique(y)) != {0, 1} or set(np.unique(vy)) != {0, 1}:
            raise ValueError("Training and validation must each contain both outcomes.")
        if epochs < 1 or patience < 1:
            raise ValueError("Epochs and patience must be positive.")
        self.mean, self.scale = x.mean(axis=0), x.std(axis=0)
        self.scale[self.scale == 0] = 1
        x, vx = (x - self.mean) / self.scale, (vx - self.mean) / self.scale
        rng = np.random.default_rng(self.seed)
        sizes = (len(FEATURES), *self.hidden, 1)
        self.weights = [rng.normal(0, np.sqrt(2 / a), (a, b)) for a, b in zip(sizes[:-1], sizes[1:])]
        self.biases = [np.zeros((1, b)) for b in sizes[1:]]
        best_loss, stale, best = float("inf"), 0, None
        self.history = []
        for epoch in range(epochs):
            activations = self._forward(x)
            delta = (activations[-1] - y) / len(x)
            grads = []
            for i in reversed(range(len(self.weights))):
                dw = activations[i].T @ delta + 0.001 * self.weights[i]
                db = delta.sum(axis=0, keepdims=True)
                grads.append((i, dw, db))
                if i:
                    delta = (delta @ self.weights[i].T) * (activations[i] > 0)
            for i, dw, db in grads:
                self.weights[i] -= 0.03 * dw
                self.biases[i] -= 0.03 * db
            train_loss = self._loss(y, self._forward(x)[-1])
            val_loss = self._loss(vy, self._forward(vx)[-1])
            self.history.append({"epoch": epoch + 1, "train_loss": train_loss, "validation_loss": val_loss})
            if val_loss < best_loss - 1e-6:
                best_loss, stale = val_loss, 0
                best = ([w.copy() for w in self.weights], [b.copy() for b in self.biases])
            else:
                stale += 1
                if stale >= patience:
                    break
        self.weights, self.biases = best
        return self

    def predict_proba(self, x):
        if self.mean is None or not self.weights:
            raise ValueError("Train or load a model before prediction.")
        return self._forward((validate_features(x) - self.mean) / self.scale)[-1].ravel()

    def to_dict(self):
        return {"hidden": list(self.hidden), "features": list(FEATURES),
                "mean": self.mean.tolist(), "scale": self.scale.tolist(),
                "weights": [w.tolist() for w in self.weights],
                "biases": [b.tolist() for b in self.biases]}

    @classmethod
    def from_dict(cls, state):
        if state["features"] != list(FEATURES):
            raise ValueError("Model feature schema does not match this application.")
        model = cls(hidden=state["hidden"])
        model.mean, model.scale = np.array(state["mean"]), np.array(state["scale"])
        model.weights = [np.array(w) for w in state["weights"]]
        model.biases = [np.array(b) for b in state["biases"]]
        sizes = (4, *model.hidden, 1)
        if (model.mean.shape != (4,) or model.scale.shape != (4,)
                or len(model.weights) != len(sizes) - 1 or len(model.biases) != len(model.weights)
                or (model.scale <= 0).any()):
            raise ValueError("Invalid model dimensions or scale.")
        for i, (w, b) in enumerate(zip(model.weights, model.biases)):
            if w.shape != (sizes[i], sizes[i + 1]) or b.shape != (1, sizes[i + 1]):
                raise ValueError("Invalid model layer dimensions.")
        if not all(np.isfinite(a).all() for a in [model.mean, model.scale, *model.weights, *model.biases]):
            raise ValueError("Model contains non-finite values.")
        return model
