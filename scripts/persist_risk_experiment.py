"""Store a validated CSV and trained model in PostgreSQL for SQL export."""
import argparse
from datetime import date
from decimal import Decimal
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.extensions import db
from app.models import RiskSnapshot, RiskExperiment
from app.repositories.risk_repository import read_snapshots, load_bundle
from app.services.neural_risk_service import prepare


def persist(csv_path, artifact_path):
    import hashlib, json
    rows, bundle = read_snapshots(csv_path), load_bundle(artifact_path)
    prepare(rows)
    fingerprint = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
    if not bundle or bundle['dataset_sha256'] != fingerprint:
        raise ValueError('The dataset does not match the trained artifact.')
    experiment = db.session.scalar(db.select(RiskExperiment).where(RiskExperiment.dataset_sha256 == fingerprint))
    if experiment:
        experiment.artifact = bundle
    else:
        db.session.add(RiskExperiment(dataset_sha256=fingerprint, artifact=bundle))
        for row in rows:
            db.session.add(RiskSnapshot(dataset_sha256=fingerprint, student_key=row['student_id'],
                snapshot_date=date.fromisoformat(row['snapshot_date']), outcome_date=date.fromisoformat(row['outcome_date']),
                prior_average=Decimal(row['prior_average']), attendance_rate=Decimal(row['attendance_rate']),
                early_average=Decimal(row['early_average']), credit_load=Decimal(row['credit_load']),
                failed_later=bool(int(row['failed_later'])), data_kind=bundle['data_kind']))
    db.session.commit()
    print(f'Persisted {len(rows)} research snapshots and model {bundle["model_version"]}.')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv',default='instance/synthetic-risk.csv')
    parser.add_argument('--artifact',default='instance/neural-risk.json')
    args=parser.parse_args()
    with create_app().app_context():
        persist(args.csv,args.artifact)
