"""Payment intents for the online payment gateway (F2).

A payment *intent* is created before the student is sent to the provider. When
the provider confirms (callback), a real :class:`Payment` row is recorded through
the existing fee service, so balances update exactly as a manual payment would.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .mixins import TimestampMixin

INTENT_STATUSES = ("pending", "paid", "failed", "cancelled", "expired")


class PaymentIntent(TimestampMixin, db.Model):
    """A single attempt to pay a student's fee balance online."""

    __tablename__ = "payment_intents"
    __table_args__ = (
        UniqueConstraint("reference", name="uq_payment_intent_reference"),
        CheckConstraint("amount > 0", name="ck_payment_intent_amount_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assessment_id: Mapped[int | None] = mapped_column(
        ForeignKey("fee_assessments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    reference: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", index=True
    )
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    checkout_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_id: Mapped[int | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    student = relationship("Student")
    assessment = relationship("FeeAssessment")
    payment = relationship("Payment")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PaymentIntent {self.reference} {self.status} {self.amount}>"
