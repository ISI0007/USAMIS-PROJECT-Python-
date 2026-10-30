"""Fee business rules: assessments, payments, balances and reporting."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from sqlalchemy.exc import IntegrityError

from ..algorithms.fee_balance import calculate_fee_balance
from ..extensions import db
from ..models import FeeAssessment, Payment, Student
from . import audit


class FeeError(ValueError):
    """Raised for invalid fee or payment input."""


def _parse_money(value, *, allow_zero: bool = False) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise FeeError("Amount must be a valid number.")
    if amount < 0 or (amount == 0 and not allow_zero):
        raise FeeError("Amount must be greater than zero.")
    return amount.quantize(Decimal("0.01"))


def student_balance(student: Student):
    """Compute a student's balance via Algorithm 3."""
    assessments = db.session.execute(
        db.select(FeeAssessment).where(FeeAssessment.student_id == student.id)
    ).scalars().all()
    payments = db.session.execute(
        db.select(Payment).where(Payment.student_id == student.id)
    ).scalars().all()

    return calculate_fee_balance(
        [{"amount": a.amount, "adjustment": a.adjustment} for a in assessments],
        [{"amount": p.amount} for p in payments],
    )


def assess_fee(actor, student: Student, category, amount, *, semester=None,
               adjustment=None, due_date=None, note: str = ""):
    """Record a fee assessment for a student."""
    amount = _parse_money(amount)
    adjustment = _parse_money(adjustment, allow_zero=True) if adjustment else Decimal("0.00")

    if adjustment > amount:
        raise FeeError("Adjustment cannot exceed the assessed amount.")

    # Application-level duplicate check first (clear message), then the DB
    # unique constraint remains the final guard against races.
    duplicate = db.session.execute(
        db.select(FeeAssessment).where(
            FeeAssessment.student_id == student.id,
            FeeAssessment.category_id == category.id,
            FeeAssessment.semester_id == (semester.id if semester else None),
        )
    ).scalars().first()
    if duplicate is not None:
        raise FeeError(
            "This student already has an assessment for that category and semester."
        )

    assessment = FeeAssessment(
        student_id=student.id,
        category_id=category.id,
        semester_id=semester.id if semester else None,
        amount=amount,
        adjustment=adjustment,
        due_date=due_date,
        note=note[:500] if note else None,
        created_by_id=actor.id,
    )
    db.session.add(assessment)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        raise FeeError("This student already has an assessment for that category and semester.")

    audit.log_action(
        "fee_assessed", "FeeAssessment", assessment.id,
        summary=f"{category.code} {amount} for student {student.student_number}",
    )
    db.session.commit()
    return assessment


def record_payment(actor, student: Student, amount, *, assessment=None,
                   reference: str = "", paid_on=None, note: str = ""):
    """Record a payment. Duplicate references and non-positive amounts are rejected."""
    amount = _parse_money(amount)

    if reference:
        existing = db.session.execute(
            db.select(Payment).where(Payment.reference == reference)
        ).scalars().first()
        if existing is not None:
            raise FeeError("A payment with that reference already exists.")

    payment = Payment(
        student_id=student.id,
        assessment_id=assessment.id if assessment else None,
        amount=amount,
        reference=reference[:48] if reference else None,
        paid_on=paid_on,
        note=note[:500] if note else None,
        recorded_by_id=actor.id,
    )
    db.session.add(payment)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        raise FeeError("A payment with that reference already exists.")

    audit.log_action(
        "payment_recorded", "Payment", payment.id,
        summary=f"Payment {amount} from student {student.student_number}",
    )
    db.session.commit()
    return payment
