"""Attendance management."""
import datetime as dt

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Attendance, CourseOffering, Enrollment, Student, Teacher
from ..security.decorators import permission_required
from .forms import AttendanceForm

bp = Blueprint("attendance", __name__, url_prefix="/attendance")


@bp.route("/")
@login_required
@permission_required("record_attendance")
def index():
    teacher = db.session.execute(
        db.select(Teacher).where(Teacher.user_id == current_user.id)
    ).scalars().first()
    query = db.select(CourseOffering)
    if current_user.role == "teacher":
        query = query.where(CourseOffering.teacher_id == (teacher.id if teacher else -1))
    offerings = db.session.execute(query).scalars().all()
    return render_template("attendance/index.html", offerings=offerings)


@bp.route("/offering/<int:offering_id>", methods=["GET", "POST"])
@login_required
@permission_required("record_attendance")
def record(offering_id: int):
    offering = db.session.get(CourseOffering, offering_id)
    if offering is None:
        abort(404)
    _authorize_offering(offering)

    form = AttendanceForm()
    enrollments = _enrolled(offering)

    if form.validate_on_submit():
        date = form.session_date.data
        status = form.status.data
        count = 0
        for e in enrollments:
            existing = db.session.execute(
                db.select(Attendance).where(
                    Attendance.student_id == e.student_id,
                    Attendance.offering_id == offering.id,
                    Attendance.session_date == date)
            ).scalars().first()
            if existing is not None:
                existing.status = status
                existing.recorded_by_id = current_user.id
            else:
                db.session.add(Attendance(
                    student_id=e.student_id, offering_id=offering.id,
                    session_date=date, status=status, recorded_by_id=current_user.id))
            count += 1
        db.session.commit()
        from ..services import audit
        audit.log_action("attendance_recorded", "CourseOffering", offering.id,
                         summary=f"{status} for {count} students on {date}")
        db.session.commit()
        flash(f"Attendance recorded for {count} student(s).", "success")
        return redirect(url_for("attendance.record", offering_id=offering.id))

    recent = db.session.execute(
        db.select(Attendance).where(Attendance.offering_id == offering.id)
        .order_by(Attendance.session_date.desc()).limit(50)
    ).scalars().all()
    return render_template("attendance/record.html", offering=offering, form=form,
                           enrollments=enrollments, recent=recent)


@bp.route("/my")
@login_required
@permission_required("view_own_attendance")
def my_attendance():
    student = db.session.execute(
        db.select(Student).where(Student.user_id == current_user.id)
    ).scalars().first()
    if student is None:
        return render_template("dashboard/no_profile.html")
    rows = db.session.execute(
        db.select(Attendance).where(Attendance.student_id == student.id)
        .order_by(Attendance.session_date.desc())
    ).scalars().all()
    present = sum(1 for r in rows if r.status in ("present", "late"))
    return render_template("attendance/my.html", rows=rows, total=len(rows), present=present)


def _authorize_offering(offering: CourseOffering) -> None:
    if current_user.has_permission("manage_enrollments"):
        return
    teacher = db.session.execute(
        db.select(Teacher).where(Teacher.user_id == current_user.id)
    ).scalars().first()
    if teacher is None or offering.teacher_id != teacher.id:
        abort(403)


def _enrolled(offering: CourseOffering):
    return db.session.execute(
        db.select(Enrollment).where(
            Enrollment.offering_id == offering.id,
            Enrollment.status.in_(("enrolled", "completed")))
    ).scalars().all()
