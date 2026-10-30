"""Layer 4: read training snapshots and atomically persist model artifacts."""
import csv
import json
import os
import tempfile
from pathlib import Path


def read_snapshots(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def save_bundle(path, bundle):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(bundle, stream, allow_nan=False, indent=2)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_bundle(path):
    try:
        with Path(path).open(encoding="utf-8") as stream:
            return json.load(stream)
    except FileNotFoundError:
        return None


def latest_database_bundle():
    from ..extensions import db
    from ..models import RiskExperiment
    experiment=db.session.scalar(db.select(RiskExperiment).order_by(RiskExperiment.created_at.desc()).limit(1))
    return experiment.artifact if experiment else None
