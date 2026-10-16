"""Algorithm 5 — Logistic Regression Classifier (AI/ML learning algorithm).

This is a *real, trained machine-learning model* implemented from first
principles — no scikit-learn dependency. It learns a logistic-regression
classifier by **gradient descent** on the institution's own student data, then
uses the learned weights to predict each student's academic-risk class.

What makes it a genuine learning algorithm (and not a fixed formula):

  * **Features** are built from stored records (credit-weighted average,
    attendance rate, credit load, assessment load).
  * **Labels** are derived from observable outcomes already in the database
    (a student is labelled "at risk" if their average is below the pass line or
    attendance is below the institutional threshold).
  * **Training** runs batch gradient descent with L2 regularisation over the
    standardised features, minimising log-loss until convergence.
  * **Prediction** applies the learned weights to new students.

Everything is deterministic (fixed seed-free initialisation at zero, fixed
learning rate/iterations) so results are reproducible and auditable.

Pure NumPy. See ``docs/ALGORITHMS.md``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

import numpy as np

# --- Model hyper-parameters (documented, auditable) -------------------------
LEARNING_RATE = 0.30
ITERATIONS = 2000
L2_LAMBDA = 0.01
FEATURE_NAMES = [
    "weighted_average_std",
    "attendance_rate_std",
    "credit_load_std",
    "assessment_load_std",
]

# Label thresholds used to derive the ground-truth class from stored records.
PASS_LINE = 60.0            # average below this => academically at risk
ATTENDANCE_FLOOR = 0.75     # attendance below this => at risk
DECISION_THRESHOLD = 0.5    # predicted probability >= this => "at risk"


@dataclass
class TrainingReport:
    """Summary of a training run (for the UI / report)."""

    samples: int
    positives: int
    negatives: int
    iterations: int
    learning_rate: float
    l2_lambda: float
    final_loss: float
    initial_loss: float
    converged: bool
    weights: list[float] = field(default_factory=list)
    feature_names: list[str] = field(default_factory=list)
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0

    def as_dict(self) -> dict:
        return {
            "samples": self.samples,
            "positives": self.positives,
            "negatives": self.negatives,
            "iterations": self.iterations,
            "learning_rate": self.learning_rate,
            "l2_lambda": self.l2_lambda,
            "initial_loss": self.initial_loss,
            "final_loss": self.final_loss,
            "loss_reduction_pct": (
                round((1 - self.final_loss / self.initial_loss) * 100, 1)
                if self.initial_loss else 0.0),
            "converged": self.converged,
            "weights": self.weights,
            "feature_names": self.feature_names,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
        }


@dataclass
class StudentPrediction:
    """A trained-model prediction for one student."""

    student_id: int
    probability: Decimal
    predicted_at_risk: bool
    contributions: list[tuple[str, float]] = field(default_factory=list)
    has_data: bool = True


def _sigmoid(z: np.ndarray) -> np.ndarray:
    """Numerically stable logistic function."""
    z = np.clip(z, -500, 500)
    return 1.0 / (1.0 + np.exp(-z))


def _q(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class LogisticRiskModel:
    """Logistic-regression classifier trained by gradient descent.

    Usage::

        model = LogisticRiskModel()
        report = model.fit(X_raw, y)          # learn from data
        probs = model.predict_proba(X_raw)    # apply to any rows
    """

    def __init__(self) -> None:
        self.weights: np.ndarray | None = None
        self.mean: np.ndarray | None = None
        self.std: np.ndarray | None = None
        self.report: TrainingReport | None = None

    # -- feature standardisation -------------------------------------------
    def _standardise(self, X: np.ndarray, *, fit: bool) -> np.ndarray:
        if fit:
            self.mean = X.mean(axis=0)
            self.std = X.std(axis=0)
            self.std[self.std == 0] = 1.0  # guard against zero variance
        return (X - self.mean) / self.std

    # -- training ----------------------------------------------------------
    def fit(self, X_raw: np.ndarray, y: np.ndarray) -> TrainingReport:
        """Train with batch gradient descent minimising log-loss + L2."""
        X = np.asarray(X_raw, dtype=float)
        y = np.asarray(y, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        n_samples, n_features = X.shape

        Xs = self._standardise(X, fit=True)
        Xb = np.hstack([np.ones((n_samples, 1)), Xs])  # bias column
        w = np.zeros(n_features + 1)

        def loss_of(w_vec: np.ndarray) -> float:
            z = Xb @ w_vec
            p = _sigmoid(z)
            eps = 1e-12
            ll = -(y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps)).mean()
            reg = (L2_LAMBDA / (2 * n_samples)) * np.sum(w_vec[1:] ** 2)
            return float(ll + reg)

        initial_loss = loss_of(w)
        prev_loss = initial_loss
        converged = False
        iters_done = 0

        for i in range(ITERATIONS):
            z = Xb @ w
            p = _sigmoid(z)
            grad = (Xb.T @ (p - y)) / n_samples
            reg_grad = np.concatenate([[0.0], (L2_LAMBDA / n_samples) * w[1:]])
            w = w - LEARNING_RATE * (grad + reg_grad)
            iters_done = i + 1

            if i % 25 == 0:
                cur = loss_of(w)
                # Relative improvement per 25-iteration window. A classifier on a
                # small, separable dataset tails off slowly, so 1e-3 (0.1% per
                # window) is the practical convergence point.
                denom = max(abs(prev_loss), 1e-12)
                if abs(prev_loss - cur) / denom < 1e-3:
                    converged = True
                    break
                prev_loss = cur

        self.weights = w
        final_loss = loss_of(w)
        # Also treat a near-zero loss as converged (perfectly separable data).
        if not converged and final_loss < 1e-3:
            converged = True

        # Evaluate on the training data (honest: training-set metrics).
        preds = (self.predict_proba_raw(X_raw) >= DECISION_THRESHOLD).astype(float)
        tp = float(np.sum((preds == 1) & (y == 1)))
        tn = float(np.sum((preds == 0) & (y == 0)))
        fp = float(np.sum((preds == 1) & (y == 0)))
        fn = float(np.sum((preds == 0) & (y == 1)))
        accuracy = (tp + tn) / max(len(y), 1)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

        self.report = TrainingReport(
            samples=n_samples,
            positives=int(np.sum(y == 1)),
            negatives=int(np.sum(y == 0)),
            iterations=iters_done,
            learning_rate=LEARNING_RATE,
            l2_lambda=L2_LAMBDA,
            initial_loss=round(initial_loss, 6),
            final_loss=round(final_loss, 6),
            converged=converged,
            weights=[round(float(v), 4) for v in w],
            feature_names=["bias", *FEATURE_NAMES],
            accuracy=round(accuracy, 4),
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1=round(f1, 4),
        )
        return self.report

    # -- inference ---------------------------------------------------------
    def predict_proba_raw(self, X_raw: np.ndarray) -> np.ndarray:
        """Probability of 'at risk' for raw (unstandardised) feature rows."""
        if self.weights is None:
            raise RuntimeError("Model is not trained; call fit() first.")
        X = np.asarray(X_raw, dtype=float)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        Xs = (X - self.mean) / self.std
        Xb = np.hstack([np.ones((Xs.shape[0], 1)), Xs])
        return _sigmoid(Xb @ self.weights)

    def contributions(self, x_raw: np.ndarray) -> list[tuple[str, float]]:
        """Per-feature contribution to the logit (for explainability)."""
        if self.weights is None:
            raise RuntimeError("Model is not trained; call fit() first.")
        x = np.asarray(x_raw, dtype=float)
        xs = (x - self.mean) / self.std
        out = [("bias", round(float(self.weights[0]), 3))]
        for name, xs_i, wi in zip(FEATURE_NAMES, xs, self.weights[1:]):
            out.append((name, round(float(xs_i * wi), 3)))
        return out
