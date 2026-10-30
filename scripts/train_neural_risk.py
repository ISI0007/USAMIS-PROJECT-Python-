"""Offline training entry point. Never trains during a web request."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.neural_risk_service import train_from_csv

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("csv")
parser.add_argument("--output", default="instance/neural-risk.json")
parser.add_argument("--data-kind", choices=["synthetic", "observed"], required=True)
parser.add_argument("--source", required=True)

if __name__ == "__main__":
    args = parser.parse_args()
    bundle = train_from_csv(args.csv, args.output, data_kind=args.data_kind, source=args.source)
    print(json.dumps({k: bundle[k] for k in ("data_kind", "model_version", "split_counts", "results", "selected_by_validation_f1")}, indent=2))
