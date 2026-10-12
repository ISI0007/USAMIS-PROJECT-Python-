"""Parent portal (F5).

A read-only area for guardians. A parent account may only ever see the
students linked to it via :class:`app.models.ParentLink`; every detail route
re-checks that ownership with ``parent_service.link_for``.
"""
from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Attendance, Enrollment, Grade, Student
from ..security.decorators import permission_required
from ..services import fee_service, parent_service, prediction_service
from ..algorithms.academic_performance import calculate_performance

bp = Blueprint("parents", __name__, url_prefix="/parents")


def _owned_student_or_404(student_id: int) -> Student:
    """Load a student, aborting 404 unless the current parent is linked to it."""
    student = db.session.get(Student, student_id)
    if student is None:
        abort(404)
    if parent_service.link_for(current_user, student) is None:
        # 404 (not 403) so a parent cannot probe which student IDs exist.
        abort(404)
    return student


@bp.route("/")
@login_required
@permission_required("view_linked_students")
def index():
    """List the students linked to this parent."""
    children = parent_service.linked_students(current_user)
    rows = []
    for student in children:
        prediction, signals = prediction_service.predict_for_student(student)
        rows.append({
            "student": student,
            "link": parent_service.link_for(current_user, student),
            "average": signals["weighted_average"],
            "attendance_rate": signals["attendance_rate"],
            "prediction": prediction,
        })
    return render_template(
        "parents/index.html",
        rows=rows,
        relationship_label=parent_service.relationship_label,
    )


@bp.route("/student/<int:student_id>")
@login_required
@permission_required("view_linked_students")
def student_detail(student_id: int):
    """A single child's grades, attendance, fees and risk — read-only."""
    student = _owned_student_or_404(student_id)

    enrollments = db.session.execute(
        db.select(Enrollment).where(Enrollment.student_id == student.id)
        .order_by(Enrollment.requested_at.desc())
    ).scalars().all()

    grades = db.session.execute(
        db.select(Grade).where(
            Grade.student_id == student.id, Grade.is_published.is_(True)
        )
    ).scalars().all()

    performance = calculate_performance([
        {
            "course_code": g.enrollment.offering.course.code,
            "credits": g.enrollment.offering.course.credits,
            "score": g.score,
            "published": g.is_published,
        }
        for g in grades
    ])

    attendance_rows = db.session.execute(
        db.select(Attendance).where(Attendance.student_id == student.id)
    ).scalars().all()
    present = sum(1 for a in attendance_rows if a.status in ("present", "late"))
    attendance_pct = round((present / len(attendance_rows) * 100.0), 1) if attendance_rows else 0.0

    balance = fee_service.student_balance(student)
    prediction, _signals = prediction_service.predict_for_student(student)

    return render_template(
        "parents/detail.html",
        student=student,
        link=parent_service.link_for(current_user, student),
        enrollments=enrollments,
        grades=grades,
        performance=performance,
        attendance_total=len(attendance_rows),
        attendance_present=present,
        attendance_pct=attendance_pct,
        balance=balance,
        prediction=prediction,
    )
