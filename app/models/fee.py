"""Fee categories, fee assessments and payments.

All monetary values use ``Numeric(12, 2)`` — decimal-safe arithmetic, never
binary floating point.
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
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
from .mixins import TimestampMixin, utcnow


class FeeCategory(TimestampMixin, db.Model):
    __tablename__ = "fee_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(24), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)

    assessments = relationship("FeeAssessment", back_populates="category")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<FeeCategory {self.code}>"


class FeeAssessment(TimestampMixin, db.Model):
    """An amount assessed (invoiced) to a student, optionally tied to a semester."""

    __tablename__ = "fee_assessments"
    __table_args__ = (
        UniqueConstraint("student_id", "category_id", "semester_id",
                         name="uq_fee_assessment_student_category_semester"),
        CheckConstraint("amount >= 0", name="ck_fee_amount_non_negative"),
        CheckConstraint("adjustment >= 0", name="ck_fee_adjustment_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("fee_categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    semester_id: Mapped[int | None] = mapped_column(
        ForeignKey("semesters.id", ondelete="SET NULL"), nullable=True, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # Explicit adjustments (waivers/scholarships) recorded as a non-negative
    # amount that reduces the amount owed.
    adjustment: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    student = relationship("Student", back_populates="fee_assessments")
    category = relationship("FeeCategory", back_populates="assessments")
    semester = relationship("Semester")
    payments = relationship("Payment", back_populates="assessment")

    @property
    def net_amount(self) -> Decimal:
        return (self.amount or Decimal("0.00")) - (self.adjustment or Decimal("0.00"))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<FeeAssessment s{self.student_id} {self.amount}>"


class Payment(TimestampMixin, db.Model):
    """A recorded payment against a fee assessment.

    This is an academic fee *recording* module, not a payment gateway. No
    real online payment is processed.
    """

    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("reference", name="uq_payment_reference"),
        CheckConstraint("amount > 0", name="ck_payment_amount_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assessment_id: Mapped[int | None] = mapped_column(
        ForeignKey("fee_assessments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(48), nullable=True, unique=True)
    paid_on: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    student = relationship("Student", back_populates="payments")
    assessment = relationship("FeeAssessment", back_populates="payments")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Payment s{self.student_id} {self.amount}>"
