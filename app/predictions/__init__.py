"""AI performance-prediction views (F4).

Staff/teacher-facing cohort risk view plus a per-student detail page. All
predictions come from :mod:`app.services.prediction_service`; nothing here is
fabricated.
"""
from flask import Blueprint, abort, render_template, request
from flask_login import login_required
from sqlalchemy import func

from ..extensions import db
from ..models import Student
from ..security.decorators import permission_required
from ..services import prediction_service

bp = Blueprint("predictions", __name__, url_prefix="/predictions")


def _students_for_cohort() -> list[Student]:
    return db.session.execute(
        db.select(Student).order_by(Student.student_number)
    ).scalars().all()


@bp.route("/")
@login_required
@permission_required("view_grades")
def index():
    """Cohort risk board — highest risk first."""
    band = request.args.get("band") or ""
    rows = prediction_service.predict_cohort(_students_for_cohort())
    if band:
        rows = [r for r in rows if r["prediction"].band == band]

    summary = {"low": 0, "medium": 0, "high": 0}
    for r in prediction_service.predict_cohort(_students_for_cohort()):
        summary[r["prediction"].band] += 1

    return render_template(
        "predictions/index.html",
        rows=rows,
        summary=summary,
        band=band,
        total=sum(summary.values()),
    )


@bp.route("/student/<int:student_id>")
@login_required
@permission_required("view_grades")
def student_detail(student_id: int):
    """Explainable prediction for a single student."""
    student = db.session.get(Student, student_id)
    if student is None:
        abort(404)
    prediction, signals = prediction_service.predict_for_student(student)
    return render_template(
        "predictions/detail.html",
        student=student,
        prediction=prediction,
        signals=signals,
        band_label=prediction_service.band_label(prediction.band),
        action=prediction_service.recommended_action(prediction.band),
        grade_count=db.session.scalar(
            db.select(func.count()).select_from(Student).where(Student.id == student.id)
        ),
    )
