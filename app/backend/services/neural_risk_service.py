"""Layer 3: validate snapshots, train models and report independent results."""
from datetime import date, datetime, timezone
import hashlib
import json

import numpy as np

from ..algorithms.neural_risk import FEATURES, NeuralRiskModel, metrics, validate_features
from ..repositories import risk_repository


def load_experiment(path):
    bundle=risk_repository.load_bundle(path)
    if bundle is None:
        from flask import has_app_context
        if has_app_context():
            return risk_repository.latest_database_bundle()
    return bundle


def prepare(rows):
    if len(rows) < 60:
        raise ValueError("At least 60 independent student snapshots are required for this experiment.")
    ids, x, y = [], [], []
    for row in rows:
        sid = row["student_id"].strip()
        if not sid or sid in ids:
            raise ValueError("Use exactly one snapshot per distinct student to prevent split leakage.")
        if date.fromisoformat(row["snapshot_date"]) >= date.fromisoformat(row["outcome_date"]):
            raise ValueError("The outcome must occur after the feature snapshot.")
        outcome = int(row["failed_later"])
        if outcome not in (0, 1):
            raise ValueError("failed_later must be 0 or 1.")
        ids.append(sid)
        x.append([float(row[name]) for name in FEATURES])
        y.append(outcome)
    x, y = validate_features(x), np.array(y)
    if min(np.sum(y == 0), np.sum(y == 1)) < 15:
        raise ValueError("At least 15 students in each outcome class are needed.")
    return ids, x, y


def split_indices(y, seed=42):
    rng = np.random.default_rng(seed)
    splits = [[], [], []]
    for label in (0, 1):
        group = rng.permutation(np.flatnonzero(y == label))
        a, b = int(len(group) * .6), int(len(group) * .8)
        for out, part in zip(splits, (group[:a], group[a:b], group[b:])):
            out.extend(part.tolist())
    return [np.array(s, dtype=int) for s in splits]


def train_from_csv(csv_path, artifact_path, *, data_kind, source):
    if data_kind not in {"synthetic", "observed"} or not source.strip():
        raise ValueError("Specify synthetic/observed data and its source.")
    rows = risk_repository.read_snapshots(csv_path)
    ids, x, y = prepare(rows)
    train, val, test = split_indices(y)
    results, states, histories = {}, {}, {}
    for name, hidden in (("logistic_regression", ()), ("neural_network", (32, 16))):
        model = NeuralRiskModel(hidden=hidden).fit(x[train], y[train], x[val], y[val])
        results[name] = {"validation": metrics(y[val], model.predict_proba(x[val])),
                         "test": metrics(y[test], model.predict_proba(x[test])),
                         "epochs": len(model.history)}
        states[name], histories[name] = model.to_dict(), model.history
    # Select only with validation results; the test set is never used for selection.
    selected = max(results, key=lambda name: results[name]["validation"]["f1"])
    fingerprint = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
    bundle = {"schema_version": 1, "model_version": fingerprint[:12],
              "trained_at": datetime.now(timezone.utc).isoformat(),
              "data_kind": data_kind, "source": source, "dataset_sha256": fingerprint,
              "target": "Failure after the snapshot date", "threshold": .5,
              "split_counts": dict(zip(("train", "validation", "test"), map(len, (train, val, test)))),
              "split_strategy": "Stratified 60/20/20, unique students, seed 42",
              "selected_by_validation_f1": selected, "results": results,
              "models": states, "history": histories}
    risk_repository.save_bundle(artifact_path, bundle)
    return bundle


def predict(bundle, values):
    model = NeuralRiskModel.from_dict(bundle["models"]["neural_network"])
    score = float(model.predict_proba(values)[0])
    return {"score": score, "above_threshold": score >= bundle["threshold"],
            "model_version": bundle["model_version"], "data_kind": bundle["data_kind"]}
