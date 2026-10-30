"""AI performance-prediction views (F4).

Staff/teacher-facing cohort risk view plus a per-student detail page. All
predictions come from :mod:`app.services.prediction_service`; nothing here is
fabricated.
"""
from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import login_required
from sqlalchemy import func

from ..extensions import db
from ..models import Student
from ..security.decorators import permission_required
from ..services import ml_training_service, prediction_service

bp = Blueprint("predictions", __name__, url_prefix="/predictions")

# Register the additional research workflow on this blueprint.
from . import neural_views  # noqa: E402,F401


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


@bp.route("/ml")
@login_required
@permission_required("view_grades")
def ml_model():
    """AI/ML page: train the logistic-regression classifier and show results."""
    force = request.args.get("train") == "1"
    result = ml_training_service.predict_cohort_ml()
    if force:
        ml_training_service.train_model(force=True)
        result = ml_training_service.predict_cohort_ml()
    return render_template(
        "predictions/ml.html",
        report=result["report"],
        rows=result["rows"],
        trained=result["trained"],
        threshold=ml_training_service.DECISION_THRESHOLD,
        weight_pairs=list(zip(result["report"].feature_names, result["report"].weights)),
    )


@bp.route("/ml/train", methods=["POST"])
@login_required
@permission_required("view_grades")
def ml_train():
    """Retrain the model and return the fresh training report as JSON."""
    model, report, raw = ml_training_service.train_model(force=True)
    return jsonify({"ok": True, "report": report.as_dict()})


@bp.route("/ml/predict/<int:student_id>")
@login_required
@permission_required("view_grades")
def ml_predict(student_id: int):
    """Predict one student with the trained model; return JSON."""
    out = ml_training_service.predict_student_ml(student_id)
    if out is None:
        return jsonify({"ok": False, "error": "student not found or no data"}), 404
    student = out.get("student")
    return jsonify({
        "ok": True,
        "student_id": student_id,
        "student": {
            "id": student.id,
            "student_number": getattr(student, "student_number", None),
            "full_name": getattr(student, "full_name", None),
        } if student is not None else None,
        "probability": round(out["probability"], 4),
        "predicted_at_risk": out["predicted_at_risk"],
        "weighted_average": (
            float(out["weighted_average"])
            if out.get("weighted_average") is not None else None
        ),
        "attendance_rate": (
            round(float(out["attendance_rate"]), 4)
            if out.get("attendance_rate") is not None else None
        ),
        "contributions": out["contributions"],
    })
