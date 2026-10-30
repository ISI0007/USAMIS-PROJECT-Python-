"""Online payment gateway (F2).

Students and parents can start a payment for an outstanding balance; the
provider callback (or, in development, the stub return URL) confirms it and
records a real fee payment.
"""
from flask import (
    Blueprint, abort, current_app, flash, redirect, render_template, request,
    url_for,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..models import PaymentIntent, Student
from ..security.decorators import permission_required
from ..services import fee_service, payment_gateway_service
from ..services.payment_gateway_service import PaymentGatewayError

bp = Blueprint("payments", __name__, url_prefix="/payments")


def _student_for_current_user() -> Student | None:
    return db.session.execute(
        db.select(Student).where(Student.user_id == current_user.id)
    ).scalars().first()


@bp.route("/")
@login_required
@permission_required("manage_fees")
def index():
    """All payment intents, newest first (finance/administrator view)."""
    status = request.args.get("status") or ""
    stmt = db.select(PaymentIntent).order_by(PaymentIntent.created_at.desc())
    if status:
        stmt = stmt.where(PaymentIntent.status == status)
    intents = db.session.execute(stmt.limit(200)).scalars().all()
    return render_template(
        "payments/index.html", intents=intents, status=status,
        statuses=("pending", "paid", "failed", "cancelled", "expired"),
    )


@bp.route("/my")
@login_required
@permission_required("view_own_fees")
def my_payments():
    student = _student_for_current_user()
    if student is None:
        return render_template("dashboard/no_profile.html")
    intents = db.session.execute(
        db.select(PaymentIntent).where(PaymentIntent.student_id == student.id)
        .order_by(PaymentIntent.created_at.desc())
    ).scalars().all()
    balance = fee_service.student_balance(student)
    return render_template("payments/my.html", student=student,
                           intents=intents, balance=balance)


@bp.route("/start", methods=["POST"])
@login_required
@permission_required("view_own_fees")
def start():
    """Start a payment for the logged-in student's outstanding balance."""
    student = _student_for_current_user()
    if student is None:
        abort(404)

    amount = request.form.get("amount") or ""
    try:
        intent = payment_gateway_service.start_intent(current_user, student, amount)
    except (fee_service.FeeError, PaymentGatewayError) as exc:
        flash(str(exc), "danger")
        return redirect(url_for("payments.my_payments"))

    if intent.status == "failed":
        flash(f"Could not start payment: {intent.error}", "danger")
        return redirect(url_for("payments.my_payments"))

    # In development the stub checkout URL is shown directly so the full flow is
    # exercisable offline. A real provider would 302 the browser to checkout.
    flash("Payment started - complete checkout to settle your balance.", "success")
    return redirect(url_for("payments.checkout", intent_id=intent.id))


@bp.route("/<int:intent_id>/checkout")
@login_required
@permission_required("view_own_fees")
def checkout(intent_id: int):
    intent = db.session.get(PaymentIntent, intent_id)
    if intent is None:
        abort(404)
    student = _student_for_current_user()
    if student is None or intent.student_id != student.id:
        abort(403)
    return render_template("payments/checkout.html", intent=intent)


@bp.route("/callback", methods=["POST"])
def callback():
    """Provider callback / webhook. Confirms a pending intent.

    In development this is triggered by the stub checkout page. A real provider
    would POST a signed payload here; signature verification lives in the
    provider adapter (out of scope for the stub).
    """
    reference = (request.form.get("reference") or request.args.get("reference") or "").strip()
    provider_ref = (request.form.get("provider_ref") or "").strip()
    if not reference:
        abort(400)

    intent = db.session.execute(
        db.select(PaymentIntent).where(PaymentIntent.reference == reference)
    ).scalars().first()
    if intent is None:
        abort(404)

    actor = current_user if current_user.is_authenticated else None
    try:
        payment_gateway_service.confirm_intent(actor, intent)
    except PaymentGatewayError as exc:
        current_app.logger.warning("payment callback rejected: %s", exc)
        abort(409)

    flash("Payment confirmed. Thank you!", "success")
    if current_user.is_authenticated:
        return redirect(url_for("payments.my_payments"))
    return redirect(url_for("auth.login"))
