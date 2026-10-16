"""AI/ML training service — trains the logistic-regression risk model from the
institution's own data and exposes predictions for the UI.

No fabricated inputs: features and labels are derived from published grades,
attendance records, enrollments and fee assessments already in the database.
"""
from __future__ import annotations

import numpy as np

from ..algorithms.logistic_risk_model import (
    ATTENDANCE_FLOOR,
    DECISION_THRESHOLD,
    PASS_LINE,
    LogisticRiskModel,
    StudentPrediction,
    TrainingReport,
)
from ..algorithms.academic_performance import calculate_performance
from ..extensions import db
from ..models import (
    Attendance, Course, CourseOffering, Enrollment, FeeAssessment, Grade, Student,
)

# Module-level cache so the cohort page and the single-student page share one
# trained model per process (training is fast, but re-training per request is
# wasteful). Invalidated when the dataset size changes.
_CACHE: dict = {"signature": None, "model": None, "report": None, "features": None}


def _student_feature_rows() -> tuple[list[int], np.ndarray, np.ndarray, list[dict]]:
    """Build (student_ids, X, y, raw_signals) from stored records."""
    students = db.session.execute(
        db.select(Student).order_by(Student.id)).scalars().all()

    ids: list[int] = []
    rows: list[list[float]] = []
    labels: list[int] = []
    raw: list[dict] = []

    for student in students:
        # --- grades -> weighted average ---
        grade_rows = db.session.execute(
            db.select(Grade, Course)
            .join(Enrollment, Grade.enrollment_id == Enrollment.id)
            .join(CourseOffering, Enrollment.offering_id == CourseOffering.id)
            .join(Course, CourseOffering.course_id == Course.id)
            .where(Grade.student_id == student.id)
        ).all()
        records = [{"course_code": c.code, "credits": c.credits,
                    "score": g.score, "published": g.is_published}
                   for g, c in grade_rows]
        performance = calculate_performance(records)
        weighted_average = performance.weighted_average

        # --- attendance rate ---
        att = db.session.execute(
            db.select(Attendance).where(Attendance.student_id == student.id)
        ).scalars().all()
        total = len(att)
        present = sum(1 for a in att if a.status in ("present", "late"))
        attendance_rate = (present / total) if total else None

        # --- credit load + assessment load ---
        credit_load = db.session.scalar(
            db.select(db.func.coalesce(db.func.sum(Course.credits), 0))
            .join(CourseOffering, CourseOffering.course_id == Course.id)
            .join(Enrollment, Enrollment.offering_id == CourseOffering.id)
            .where(Enrollment.student_id == student.id)) or 0
        assessment_count = db.session.scalar(
            db.select(db.func.count(FeeAssessment.id))
            .where(FeeAssessment.student_id == student.id)) or 0

        # Skip students with no academic signal at all (cannot label honestly).
        if weighted_average is None and attendance_rate is None:
            continue

        wa = float(weighted_average) if weighted_average is not None else PASS_LINE
        ar = float(attendance_rate) if attendance_rate is not None else ATTENDANCE_FLOOR

        # Ground-truth label from observable outcomes.
        at_risk = int(wa < PASS_LINE or ar < ATTENDANCE_FLOOR)

        ids.append(student.id)
        rows.append([wa, ar, float(credit_load), float(assessment_count)])
        labels.append(at_risk)
        raw.append({
            "student": student,
            "weighted_average": weighted_average,
            "attendance_rate": attendance_rate,
            "credit_load": int(credit_load),
            "assessment_count": int(assessment_count),
            "label_at_risk": bool(at_risk),
        })

    X = np.asarray(rows, dtype=float) if rows else np.empty((0, 4))
    y = np.asarray(labels, dtype=float) if labels else np.empty((0,))
    return ids, X, y, raw


def train_model(force: bool = False) -> tuple[LogisticRiskModel, TrainingReport, list[dict]]:
    """Train (or fetch cached) the logistic-regression risk model."""
    ids, X, y, raw = _student_feature_rows()
    signature = (len(ids), int(y.sum()) if len(y) else 0)

    if not force and _CACHE["signature"] == signature and _CACHE["model"] is not None:
        return _CACHE["model"], _CACHE["report"], _CACHE["features"]

    model = LogisticRiskModel()
    if len(ids) == 0:
        # Nothing to train on — return an untrained, empty report.
        report = TrainingReport(
            samples=0, positives=0, negatives=0, iterations=0,
            learning_rate=0.0, l2_lambda=0.0, initial_loss=0.0, final_loss=0.0,
            converged=False, feature_names=["bias"])
        _CACHE.update(signature=signature, model=model, report=report, features=raw)
        return model, report, raw

    report = model.fit(X, y)
    _CACHE.update(signature=signature, model=model, report=report, features=raw)
    return model, report, raw


def predict_cohort_ml() -> dict:
    """Train and predict every student; return the report + per-student rows."""
    model, report, raw = train_model()
    if report.samples == 0:
        return {"report": report, "rows": [], "trained": False}

    preds = []
    for item in raw:
        wa = float(item["weighted_average"]) if item["weighted_average"] is not None else PASS_LINE
        ar = float(item["attendance_rate"]) if item["attendance_rate"] is not None else ATTENDANCE_FLOOR
        x = np.array([wa, ar, float(item["credit_load"]), float(item["assessment_count"])])
        proba = float(model.predict_proba_raw(x)[0])
        contribs = model.contributions(x)
        # Top driver by absolute contribution (excluding bias).
        top = max(contribs[1:], key=lambda c: abs(c[1])) if len(contribs) > 1 else ("", 0.0)
        preds.append({
            "student": item["student"],
            "probability": proba,
            "predicted_at_risk": proba >= DECISION_THRESHOLD,
            "weighted_average": item["weighted_average"],
            "attendance_rate": item["attendance_rate"],
            "contributions": contribs,
            "top_driver": top[0],
        })

    preds.sort(key=lambda r: r["probability"], reverse=True)
    return {"report": report, "rows": preds, "trained": True}


def predict_student_ml(student_id: int) -> dict | None:
    """Predict one student with the trained model + explainability."""
    model, report, raw = train_model()
    item = next((r for r in raw if r["student"].id == student_id), None)
    if item is None:
        return None
    wa = float(item["weighted_average"]) if item["weighted_average"] is not None else PASS_LINE
    ar = float(item["attendance_rate"]) if item["attendance_rate"] is not None else ATTENDANCE_FLOOR
    x = np.array([wa, ar, float(item["credit_load"]), float(item["assessment_count"])])
    proba = float(model.predict_proba_raw(x)[0])
    return {
        "student": item["student"],
        "probability": proba,
        "predicted_at_risk": proba >= DECISION_THRESHOLD,
        "weighted_average": item["weighted_average"],
        "attendance_rate": item["attendance_rate"],
        "credit_load": item["credit_load"],
        "assessment_count": item["assessment_count"],
        "contributions": model.contributions(x),
    }
