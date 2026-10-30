"""Enrollment management: requests, approvals, rejections and history."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import CourseOffering, Enrollment, Semester, Student
from ..security.decorators import permission_required
from ..services import enrollment_service
from .forms import EnrollmentRequestForm

bp = Blueprint("enrollments", __name__, url_prefix="/enrollments")


@bp.route("/")
@login_required
@permission_required("manage_enrollments")
def index():
    status = request.args.get("status") or ""
    page = request.args.get("page", 1, type=int)
    query = db.select(Enrollment)
    if status:
        query = query.where(Enrollment.status == status)
    pagination = db.paginate(
        query.order_by(Enrollment.requested_at.desc()),
        page=page, per_page=15, error_out=False,
    )
    return render_template("enrollments/index.html", pagination=pagination, status=status)


@bp.route("/<int:enrollment_id>/decide", methods=["POST"])
@login_required
@permission_required("manage_enrollments")
def decide(enrollment_id: int):
    approve = request.form.get("decision") == "approve"
    note = request.form.get("note", "")
    updated = enrollment_service.decide(current_user, enrollment_id, approve, note)
    if updated is None:
        flash("Could not update that request (not pending, or the course is full).", "danger")
    else:
        flash(f"Enrollment {updated.status}.", "success")
    return redirect(request.referrer or url_for("enrollments.index"))


@bp.route("/<int:enrollment_id>/drop", methods=["POST"])
@login_required
@permission_required("manage_enrollments")
def drop(enrollment_id: int):
    updated = enrollment_service.drop_enrollment(current_user, enrollment_id)
    if updated is None:
        flash("That enrollment cannot be dropped.", "danger")
    else:
        flash("Enrollment dropped.", "success")
    return redirect(request.referrer or url_for("enrollments.index"))


# ---------------------------------------------------------------------- #
# Student-facing enrollment
# ---------------------------------------------------------------------- #
@bp.route("/my")
@login_required
@permission_required("view_own_enrollment")
def my_enrollments():
    student = _current_student()
    if student is None:
        return render_template("dashboard/no_profile.html")
    rows = db.session.execute(
        db.select(Enrollment).where(Enrollment.student_id == student.id)
        .order_by(Enrollment.requested_at.desc())
    ).scalars().all()
    return render_template("enrollments/my.html", enrollments=rows, student=student)


@bp.route("/request", methods=["GET", "POST"])
@login_required
@permission_required("request_enrollment")
def request_enrollment():
    student = _current_student()
    if student is None:
        return render_template("dashboard/no_profile.html")

    form = EnrollmentRequestForm()
    _offerings(form)
    if form.validate_on_submit():
        offering = db.session.get(CourseOffering, form.offering_id.data)
        if offering is None:
            abort(404)
        enrollment, result = enrollment_service.request_enrollment(student, offering)
        if enrollment is None:
            flash(f"Enrollment rejected: {result.message}", "danger")
            for reason in result.reasons:
                flash(reason, "warning")
        else:
            flash(f"Enrollment submitted: {result.message}", "success")
            return redirect(url_for("enrollments.my_enrollments"))
    return render_template("enrollments/request.html", form=form, student=student)


@bp.route("/check/<int:offering_id>")
@login_required
@permission_required("view_own_enrollment")
def check(offering_id: int):
    """Dry-run eligibility check surfaced to the student before applying."""
    student = _current_student()
    if student is None:
        abort(403)
    offering = db.session.get(CourseOffering, offering_id)
    if offering is None:
        abort(404)
    result = enrollment_service.evaluate(student, offering)
    return render_template("enrollments/check.html", result=result, offering=offering)


def _current_student() -> Student | None:
    return db.session.execute(
        db.select(Student).where(Student.user_id == current_user.id)
    ).scalars().first()


def _offerings(form) -> None:
    active_semester = db.session.execute(
        db.select(Semester).where(Semester.registration_open.is_(True))
        .order_by(Semester.start_date.desc())
    ).scalars().all()
    offering_rows = []
    for sem in active_semester:
        for o in db.session.execute(
            db.select(CourseOffering).where(
                CourseOffering.semester_id == sem.id, CourseOffering.is_active.is_(True))
        ).scalars().all():
            offering_rows.append((o.id, f"{o.course.code} — {o.course.title} ({sem.label})"))
    form.offering_id.choices = offering_rows
