"""Online payment gateway business rules (F2).

Creates payment intents through the configured :class:`PaymentProvider` and,
on callback, records the corresponding :class:`Payment` through the existing fee
service so balances update exactly as a manual payment would.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from ..extensions import db
from ..integrations import get_payment_provider
from ..models import PaymentIntent, Student
from ..models.mixins import utcnow
from . import audit, fee_service

# A tiny state machine guard: only these transitions are permitted.
_ALLOWED_TRANSITIONS = {
    "pending": {"paid", "failed", "cancelled", "expired"},
    "paid": set(),
    "failed": {"pending"},
    "cancelled": set(),
    "expired": set(),
}


class PaymentGatewayError(ValueError):
    """Raised for invalid payment-gateway input."""


def _new_reference() -> str:
    return f"PAY-{uuid.uuid4().hex[:12].upper()}"


def start_intent(actor, student: Student, amount, *, assessment=None,
                 currency: str = "USD") -> PaymentIntent:
    """Create a payment intent and return it with a provider checkout URL."""
    money = fee_service._parse_money(amount)  # reuse the decimal-safe parser

    intent = PaymentIntent(
        student_id=student.id,
        assessment_id=assessment.id if assessment else None,
        amount=money,
        currency=currency.upper()[:8],
        reference=_new_reference(),
        status="pending",
        created_by_id=actor.id if actor else None,
    )
    db.session.add(intent)
    db.session.flush()

    provider = get_payment_provider()
    result = provider.create_intent(
        reference=intent.reference,
        amount=money,
        currency=intent.currency,
        description=f"{student.student_number} fee payment",
    )
    if not result.ok:
        intent.status = "failed"
        intent.error = result.error or "Provider could not create the intent."
    else:
        intent.provider = result.provider
        intent.provider_ref = result.provider_ref
        intent.checkout_url = result.checkout_url

    audit.log_action(
        "payment_intent_started", "PaymentIntent", intent.id,
        summary=f"{intent.reference} {money} for {student.student_number}",
    )
    db.session.commit()
    return intent


def _transition(intent: PaymentIntent, new_status: str) -> None:
    if new_status not in _ALLOWED_TRANSITIONS.get(intent.status, set()):
        raise PaymentGatewayError(
            f"Cannot move a {intent.status} intent to {new_status}."
        )
    intent.status = new_status


def confirm_intent(actor, intent: PaymentIntent) -> PaymentIntent:
    """Mark a pending intent as paid and record the matching fee payment.

    This is what the provider callback (or, in development, the stub return URL)
    invokes. Recording goes through ``fee_service.record_payment`` so audit,
    duplicate-reference protection, and balance updates behave identically to a
    manual payment.
    """
    if intent.status == "paid":
        # Idempotent: a repeated callback must not double-charge.
        return intent
    _transition(intent, "paid")

    payment = fee_service.record_payment(
        actor,
        db.session.get(Student, intent.student_id),
        intent.amount,
        assessment=(intent.assessment or None),
        reference=intent.reference,
        note=f"Online payment ({intent.provider})",
    )
    intent.payment_id = payment.id
    intent.completed_at = utcnow()
    audit.log_action(
        "payment_intent_confirmed", "PaymentIntent", intent.id,
        summary=f"{intent.reference} settled -> payment {payment.id}",
    )
    db.session.commit()
    return intent


def fail_intent(actor, intent: PaymentIntent, reason: str = "") -> PaymentIntent:
    _transition(intent, "failed")
    intent.error = (reason or "Provider reported failure.")[:500]
    audit.log_action(
        "payment_intent_failed", "PaymentIntent", intent.id,
        summary=intent.reference,
    )
    db.session.commit()
    return intent
