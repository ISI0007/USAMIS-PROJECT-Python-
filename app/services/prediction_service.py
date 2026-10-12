"""Performance-prediction service (F4).

Gathers a student's published grades and attendance from the database, runs the
explainable prediction algorithm, and returns a result the UI can render. No
fabricated inputs: every prediction is derived from stored records.
"""
from __future__ import annotations

from ..algorithms.academic_performance import calculate_performance
from ..algorithms.performance_prediction import (
    PredictionResult,
    band_label,
    predict_performance,
    recommended_action,
)
from ..extensions import db
from ..models import Attendance, Course, CourseOffering, Enrollment, Grade, Student


def student_signals(student: Student) -> dict:
    """Collect the raw signals used by the predictor for one student."""
    rows = db.session.execute(
        db.select(Grade, Course)
        .join(Enrollment, Grade.enrollment_id == Enrollment.id)
        .join(CourseOffering, Enrollment.offering_id == CourseOffering.id)
        .join(Course, CourseOffering.course_id == Course.id)
        .where(Grade.student_id == student.id)
    ).all()

    records = [
        {
            "course_code": course.code,
            "credits": course.credits,
            "score": grade.score,
            "published": grade.is_published,
        }
        for grade, course in rows
    ]
    performance = calculate_performance(records)

    attendance_rows = db.session.execute(
        db.select(Attendance).where(Attendance.student_id == student.id)
    ).scalars().all()
    total = len(attendance_rows)
    present = sum(1 for a in attendance_rows if a.status in ("present", "late"))
    attendance_rate = (present / total) if total else None

    return {
        "performance": performance,
        "weighted_average": performance.weighted_average,
        "attendance_rate": attendance_rate,
        "attendance_total": total,
        "attendance_present": present,
    }


def predict_for_student(student: Student) -> tuple[PredictionResult, dict]:
    """Return (prediction, signals) for a single student."""
    signals = student_signals(student)
    prediction = predict_performance(
        weighted_average=signals["weighted_average"],
        attendance_rate=signals["attendance_rate"],
    )
    return prediction, signals


def predict_cohort(students: list[Student]) -> list[dict]:
    """Return one prediction row per student, ordered by risk (high first)."""
    results = []
    for student in students:
        prediction, signals = predict_for_student(student)
        results.append({
            "student": student,
            "prediction": prediction,
            "band_label": band_label(prediction.band),
            "action": recommended_action(prediction.band),
            "weighted_average": signals["weighted_average"],
            "attendance_rate": signals["attendance_rate"],
        })
    # High risk first, then by descending risk score.
    results.sort(key=lambda r: float(r["prediction"].risk_score), reverse=True)
    return results
