"""Create explicitly synthetic data for a reproducible classroom experiment."""
import argparse
import csv
from pathlib import Path
import numpy as np


def generate(path, count=600):
    rng = np.random.default_rng(42)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["student_id", "snapshot_date", "outcome_date", "prior_average", "attendance_rate", "early_average", "credit_load", "failed_later"]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for i in range(count):
            prior = float(np.clip(rng.normal(65, 17), 0, 100))
            attendance = float(rng.uniform(.35, 1))
            early = float(np.clip(prior + rng.normal(0, 15), 0, 100))
            credits = int(rng.integers(12, 28))
            # Noisy later outcome, deliberately distinct from a present-state label.
            z = (58 - early) / 13 + (0.75 - attendance) * 3 + (credits - 20) * .06
            z += 0.8 * (early < 65 and attendance < .65)
            failed = int(rng.random() < 1 / (1 + np.exp(-z)))
            writer.writerow(dict(zip(fields, [f"SYN-{i:04}", "2025-03-01", "2025-06-30", round(prior, 2), round(attendance, 3), round(early, 2), credits, failed])))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="instance/synthetic-risk.csv")
    args = parser.parse_args()
    generate(args.output)
    print(f"Synthetic demonstration data written to {args.output}")
