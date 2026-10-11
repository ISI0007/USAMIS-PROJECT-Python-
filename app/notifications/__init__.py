"""Notification center: SMS dispatch and history.

F1 — SMS notifications for critical updates (e.g. fee reminders).
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..models import FeeAssessment, Payment, SmsMessage, Student
from ..security.decorators import permission_required
from ..services import notification_service
from ..services.notification_service import SmsError

bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@bp.route("/sms")
@login_required
@permission_required("send_notifications")
def sms_index():
    """SMS history with status/category filters."""
    status = request.args.get("status") or ""
    category = request.args.get("category") or ""

    stmt = db.select(SmsMessage).order_by(SmsMessage.created_at.desc())
    if status:
        stmt = stmt.where(SmsMessage.status == status)
    if category:
        stmt = stmt.where(SmsMessage.category == category)
    messages = db.session.execute(stmt.limit(200)).scalars().all()

    counts = {
        "total": db.session.scalar(db.select(func.count(SmsMessage.id))) or 0,
        "sent": db.session.scalar(
            db.select(func.count(SmsMessage.id)).where(SmsMessage.status == "sent")
        ) or 0,
        "failed": db.session.scalar(
            db.select(func.count(SmsMessage.id)).where(SmsMessage.status == "failed")
        ) or 0,
    }

    return render_template(
        "notifications/sms_index.html",
        messages=messages,
        counts=counts,
        status=status,
        category=category,
        statuses=("queued", "sent", "failed"),
        categories=("fee_reminder", "payment_received", "account", "general"),
    )


@bp.route("/sms/compose", methods=["GET", "POST"])
@login_required
@permission_required("send_notifications")
def sms_compose():
    """Compose and send a single SMS to a student or an arbitrary number."""
    students = db.session.execute(
        db.select(Student).order_by(Student.student_number)
    ).scalars().all()

    if request.method == "POST":
        student_id = request.form.get("student_id") or ""
        recipient = (request.form.get("recipient") or "").strip()
        body = (request.form.get("body") or "").strip()
        student = db.session.get(Student, int(student_id)) if student_id.isdigit() else None

        if student is not None:
            recipient = recipient or (student.phone or "")

        try:
            message = notification_service.send_sms(
                current_user, recipient, body, category="general", student=student
            )
        except SmsError as exc:
            flash(str(exc), "error")
        else:
            if message.status == "sent":
                flash(f"Message sent to {message.recipient}.", "success")
            else:
                flash(f"Message failed: {message.error}", "error")
            return redirect(url_for("notifications.sms_index"))

    return render_template("notifications/sms_compose.html", students=students)


@bp.route("/sms/fee-reminders", methods=["GET", "POST"])
@login_required
@permission_required("send_notifications")
def sms_fee_reminders():
    """Review students with outstanding balances and send fee reminders."""
    # Outstanding balance per student (assessed − adjustments − paid).
    assessed = dict(db.session.execute(
        db.select(
            FeeAssessment.student_id,
            func.sum(FeeAssessment.amount - FeeAssessment.adjustment),
        ).group_by(FeeAssessment.student_id)
    ).all())
    paid = dict(db.session.execute(
        db.select(Payment.student_id, func.sum(Payment.amount))
        .group_by(Payment.student_id)
    ).all())

    defaulters = []
    for student_id, total in assessed.items():
        outstanding = float(total or 0) - float(paid.get(student_id, 0) or 0)
        if outstanding > 0:
            student = db.session.get(Student, student_id)
            defaulters.append({
                "student": student,
                "outstanding": round(outstanding, 2),
                "has_phone": bool(student and student.phone),
            })
    defaulters.sort(key=lambda r: r["outstanding"], reverse=True)

    if request.method == "POST":
        selected = request.form.getlist("student_id")
        sent = 0
        skipped = 0
        failed = 0
        for sid in selected:
            student = db.session.get(Student, int(sid)) if sid.isdigit() else None
            if student is None or not student.phone:
                skipped += 1
                continue
            row = next((d for d in defaulters if d["student"].id == student.id), None)
            if row is None:
                skipped += 1
                continue
            try:
                message = notification_service.send_fee_reminder(
                    current_user, student, row["outstanding"]
                )
            except SmsError:
                failed += 1
            else:
                if message.status == "sent":
                    sent += 1
                else:
                    failed += 1
        flash(
            f"Fee reminders — sent: {sent}, skipped (no phone): {skipped}, failed: {failed}.",
            "success" if not failed else "warning",
        )
        return redirect(url_for("notifications.sms_index"))

    return render_template("notifications/sms_fee_reminders.html", defaulters=defaulters)
