"""Layer 4 storage for reproducible research datasets and model artifacts.

Training student keys describe an independent research cohort, not live
student-profile foreign keys. Synthetic examples never become official records.
"""
from datetime import date
from decimal import Decimal
from sqlalchemy import Boolean, CheckConstraint, Date, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..extensions import db
from .mixins import TimestampMixin


class RiskSnapshot(TimestampMixin, db.Model):
    __tablename__ = 'risk_snapshots'
    __table_args__ = (
        UniqueConstraint('dataset_sha256', 'student_key', name='uq_risk_dataset_student'),
        CheckConstraint('outcome_date > snapshot_date', name='ck_risk_outcome_after_snapshot'),
        CheckConstraint('prior_average BETWEEN 0 AND 100 AND early_average BETWEEN 0 AND 100', name='ck_risk_scores'),
        CheckConstraint('attendance_rate BETWEEN 0 AND 1 AND credit_load BETWEEN 1 AND 40', name='ck_risk_inputs'),
        CheckConstraint("data_kind IN ('synthetic','observed')", name='ck_risk_data_kind'),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    student_key: Mapped[str] = mapped_column(String(100), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    outcome_date: Mapped[date] = mapped_column(Date, nullable=False)
    prior_average: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    attendance_rate: Mapped[Decimal] = mapped_column(Numeric(7, 6), nullable=False)
    early_average: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    credit_load: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    failed_later: Mapped[bool] = mapped_column(Boolean, nullable=False)
    data_kind: Mapped[str] = mapped_column(String(16), nullable=False)


class RiskExperiment(TimestampMixin, db.Model):
    __tablename__ = 'risk_experiments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    artifact: Mapped[dict] = mapped_column(JSON, nullable=False)
