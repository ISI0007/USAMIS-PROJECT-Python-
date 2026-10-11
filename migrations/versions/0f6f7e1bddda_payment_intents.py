"""payment intents

Revision ID: 0f6f7e1bddda
Revises: 54e0a006ac18
Create Date: 2026-10-12

Adds the ``payment_intents`` table for the online payment gateway (F2).
"""
from alembic import op
import sqlalchemy as sa


revision = '0f6f7e1bddda'
down_revision = '54e0a006ac18'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payment_intents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("assessment_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False,
                  server_default="USD"),
        sa.Column("reference", sa.String(length=48), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False,
                  server_default="pending"),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("provider_ref", sa.String(length=64), nullable=True),
        sa.Column("checkout_url", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_id", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"],
                                ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assessment_id"], ["fee_assessments.id"],
                                ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"],
                                ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"],
                                ondelete="SET NULL"),
        sa.UniqueConstraint("reference", name="uq_payment_intent_reference"),
        sa.CheckConstraint("amount > 0", name="ck_payment_intent_amount_positive"),
    )
    op.create_index("ix_payment_intents_student_id", "payment_intents", ["student_id"])
    op.create_index("ix_payment_intents_assessment_id", "payment_intents", ["assessment_id"])
    op.create_index("ix_payment_intents_reference", "payment_intents", ["reference"])
    op.create_index("ix_payment_intents_status", "payment_intents", ["status"])
    op.create_index("ix_payment_intents_payment_id", "payment_intents", ["payment_id"])


def downgrade():
    op.drop_index("ix_payment_intents_payment_id", table_name="payment_intents")
    op.drop_index("ix_payment_intents_status", table_name="payment_intents")
    op.drop_index("ix_payment_intents_reference", table_name="payment_intents")
    op.drop_index("ix_payment_intents_assessment_id", table_name="payment_intents")
    op.drop_index("ix_payment_intents_student_id", table_name="payment_intents")
    op.drop_table("payment_intents")
