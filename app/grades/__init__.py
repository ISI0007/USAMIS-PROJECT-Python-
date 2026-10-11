"""Grade management: entry, publication, and reporting."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import CourseOffering, Enrollment, Grade, Student, Teacher
from ..security.decorators import permission_required
from ..services import grade_service
from .forms import GradeForm

bp = Blueprint("grades", __name__, url_prefix="/grades")


@bp.route("/")
@login_required
@permission_required("view_grades")
def index():
    teacher = db.session.execute(
        db.select(Teacher).where(Teacher.user_id == current_user.id)
    ).scalars().first()

    query = db.select(CourseOffering)
    if current_user.role == "teacher":
        if teacher is None:
            query = query.where(CourseOffering.id == -1)
        else:
            query = query.where(CourseOffering.teacher_id == teacher.id)
    offerings = db.session.execute(query.order_by(CourseOffering.id)).scalars().all()
    return render_template("grades/index.html", offerings=offerings)


@bp.route("/offering/<int:offering_id>", methods=["GET", "POST"])
@login_required
@permission_required("enter_grades")
def entry(offering_id: int):
    offering = db.session.get(CourseOffering, offering_id)
    if offering is None:
        abort(404)
    if not grade_service.teacher_teaches(current_user, offering):
        abort(403)

    form = GradeForm()
    if form.validate_on_submit():
        try:
            grade_service.record_grade(
                current_user,
                form.enrollment_id.data,
                form.score.data,
                publish=form.publish.data,
                remarks=form.remarks.data or "",
            )
            flash("Grade saved.", "success")
        except grade_service.GradeError as exc:
            flash(str(exc), "danger")
        return redirect(url_for("grades.entry", offering_id=offering.id))

    enrollments = db.session.execute(
        db.select(Enrollment).where(
            Enrollment.offering_id == offering.id,
            Enrollment.status.in_(("enrolled", "completed")))
    ).scalars().all()
    return render_template("grades/entry.html", offering=offering, enrollments=enrollments,
                           form=form)


@bp.route("/enrollment/<int:enrollment_id>", methods=["POST"])
@login_required
@permission_required("enter_grades")
def save(enrollment_id: int):
    enrollment = db.session.get(Enrollment, enrollment_id)
    if enrollment is None:
        abort(404)
    offering = db.session.get(CourseOffering, enrollment.offering_id)
    if not grade_service.teacher_teaches(current_user, offering):
        abort(403)
    try:
        grade_service.record_grade(
            current_user,
            enrollment_id,
            request.form.get("score"),
            publish=request.form.get("publish") == "on",
        )
        flash("Grade saved.", "success")
    except grade_service.GradeError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("grades.entry", offering_id=offering.id))


@bp.route("/my")
@login_required
@permission_required("view_own_grades")
def my_grades():
    student = db.session.execute(
        db.select(Student).where(Student.user_id == current_user.id)
    ).scalars().first()
    if student is None:
        return render_template("dashboard/no_profile.html")

    grades = db.session.execute(
        db.select(Grade).where(Grade.student_id == student.id, Grade.is_published.is_(True))
    ).scalars().all()

    records = [
        {
            "course_code": g.enrollment.offering.course.code,
            "credits": g.enrollment.offering.course.credits,
            "score": g.score,
            "published": g.is_published,
        }
        for g in grades
    ]
    from ..algorithms.academic_performance import calculate_performance
    from flask import current_app

    performance = calculate_performance(
        records, gpa_enabled=current_app.config.get("GPA_ENABLED", False)
    )
    return render_template("grades/my.html", grades=grades, performance=performance)
