"""SMS notification business rules.

Composes messages, forwards them to the configured :class:`SmsProvider`, and
persists the outcome. In development the stub provider records the send.
"""
from __future__ import annotations

from decimal import Decimal

from ..extensions import db
from ..integrations import get_sms_provider
from ..models import SmsMessage, Student
from ..models.mixins import utcnow
from . import audit


class SmsError(ValueError):
    """Raised for invalid SMS input."""


def _clean_phone(value: str | None) -> str | None:
    if not value:
        return None
    phone = "".join(ch for ch in str(value) if ch.isdigit() or ch == "+")
    return phone or None


def send_sms(actor, recipient: str, body: str, *, category: str = "general",
             student: Student | None = None) -> SmsMessage:
    """Persist and dispatch one SMS, recording the provider outcome."""
    phone = _clean_phone(recipient)
    if not phone:
        raise SmsError("A valid recipient phone number is required.")
    if not body or not body.strip():
        raise SmsError("Message body cannot be empty.")

    message = SmsMessage(
        recipient=phone,
        body=body.strip()[:480],
        category=category,
        student_id=student.id if student else None,
        created_by_id=actor.id if actor else None,
        status="queued",
    )
    db.session.add(message)
    db.session.flush()

    provider = get_sms_provider()
    result = provider.send(phone, message.body)
    message.provider = result.provider
    if result.ok:
        message.status = "sent"
        message.provider_ref = result.reference
        message.sent_at = utcnow()
    else:
        message.status = "failed"
        message.error = result.error or "Provider rejected the message."

    audit.log_action(
        "sms_sent" if result.ok else "sms_failed",
        "SmsMessage",
        message.id,
        summary=f"{message.category} -> {phone}",
    )
    db.session.commit()
    return message


def compose_fee_reminder(student: Student, outstanding: Decimal) -> str:
    """Build the fee-reminder text for a student with an outstanding balance."""
    name = student.full_name or student.student_number
    return (
        f"Dear {name}, your USAMIS account has an outstanding balance of "
        f"{outstanding:.2f}. Please settle it at your earliest convenience."
    )


def compose_payment_receipt(student: Student, amount: Decimal, reference: str) -> str:
    return (
        f"Payment received: {amount:.2f} for {student.student_number}. "
        f"Reference {reference}. Thank you."
    )


def send_fee_reminder(actor, student: Student, outstanding: Decimal) -> SmsMessage:
    """Send the standard fee reminder to a student's phone number."""
    return send_sms(
        actor,
        student.phone or "",
        compose_fee_reminder(student, outstanding),
        category="fee_reminder",
        student=student,
    )


def send_payment_receipt(actor, student: Student, amount: Decimal, reference: str) -> SmsMessage:
    return send_sms(
        actor,
        student.phone or "",
        compose_payment_receipt(student, amount, reference),
        category="payment_received",
        student=student,
    )
