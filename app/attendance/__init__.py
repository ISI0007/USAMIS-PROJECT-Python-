"""Attendance management."""
import datetime as dt

from flask import (
    Blueprint, abort, current_app, flash, redirect, render_template, request,
    url_for,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Attendance, AttendanceSession, CourseOffering, Enrollment, Student, Teacher
from ..security.decorators import permission_required
from ..services import qr_attendance_service
from ..services.qr_attendance_service import QRAttendanceError
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


# --------------------------------------------------------------------------
# QR-code attendance (F3)
# --------------------------------------------------------------------------
@bp.route("/offering/<int:offering_id>/session", methods=["GET", "POST"])
@login_required
@permission_required("record_attendance")
def qr_session(offering_id: int):
    """Open (or show) a QR attendance session for a course offering."""
    offering = db.session.get(CourseOffering, offering_id)
    if offering is None:
        abort(404)
    _authorize_offering(offering)

    if request.method == "POST":
        try:
            ttl = int(request.form.get("ttl_minutes") or 15)
            qr_attendance_service.open_session(
                current_user, offering, ttl_minutes=ttl,
                secret=current_app.config["SECRET_KEY"],
            )
            flash("QR attendance session opened.", "success")
        except QRAttendanceError as exc:
            flash(str(exc), "danger")
        return redirect(url_for("attendance.qr_session", offering_id=offering.id))

    session = db.session.execute(
        db.select(AttendanceSession).where(
            AttendanceSession.offering_id == offering.id,
            AttendanceSession.is_open.is_(True))
        .order_by(AttendanceSession.session_date.desc())
    ).scalars().first()

    scan_url = None
    if session is not None and session.is_active():
        scan_url = url_for("attendance.qr_scan", token=session.token, _external=True)

    present = db.session.execute(
        db.select(Attendance).where(
            Attendance.offering_id == offering.id,
            Attendance.session_date == dt.date.today())
    ).scalars().all()

    return render_template("attendance/qr_session.html", offering=offering,
                           session=session, scan_url=scan_url, present=present)


@bp.route("/offering/<int:offering_id>/session/close", methods=["POST"])
@login_required
@permission_required("record_attendance")
def qr_close(offering_id: int):
    offering = db.session.get(CourseOffering, offering_id)
    if offering is None:
        abort(404)
    _authorize_offering(offering)
    session = db.session.get(AttendanceSession, int(request.form.get("session_id") or 0))
    if session is None or session.offering_id != offering.id:
        abort(404)
    qr_attendance_service.close_session(current_user, session)
    flash("QR attendance session closed.", "success")
    return redirect(url_for("attendance.qr_session", offering_id=offering.id))


@bp.route("/scan")
@login_required
@permission_required("view_own_attendance")
def qr_scan():
    """Student-facing scan target embedded in the QR code.

    A phone camera opens this URL; the token in the query string is validated
    and the student's attendance is marked present.
    """
    token = request.args.get("token") or ""
    if not token:
        flash("No attendance token supplied.", "danger")
        return redirect(url_for("attendance.my_attendance"))
    try:
        record = qr_attendance_service.scan(
            current_user, token, secret=current_app.config["SECRET_KEY"]
        )
    except QRAttendanceError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("attendance.my_attendance"))
    flash(f"Attendance recorded ({record.status}) for {record.session_date}.", "success")
    return redirect(url_for("attendance.my_attendance"))


@bp.route("/qr/<token>.png")
@login_required
@permission_required("record_attendance")
def qr_image(token: str):
    """Render a session token as a PNG QR code (no external service)."""
    import io

    import qrcode
    from flask import send_file

    scan_url = url_for("attendance.qr_scan", token=token, _external=True)
    img = qrcode.make(scan_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")
