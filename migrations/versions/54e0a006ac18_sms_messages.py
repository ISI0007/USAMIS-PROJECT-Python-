"""sms messages

Revision ID: 54e0a006ac18
Revises: b7c1a5f0d9e2
Create Date: 2026-10-12

Adds the ``sms_messages`` table for outbound SMS notifications (F1).
"""
from alembic import op
import sqlalchemy as sa


revision = '54e0a006ac18'
down_revision = 'b7c1a5f0d9e2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sms_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recipient", sa.String(length=32), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False,
                  server_default="general"),
        sa.Column("status", sa.String(length=16), nullable=False,
                  server_default="queued"),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("provider_ref", sa.String(length=64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("student_id", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"],
                                ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"],
                                ondelete="SET NULL"),
    )
    op.create_index("ix_sms_messages_recipient", "sms_messages", ["recipient"])
    op.create_index("ix_sms_messages_category", "sms_messages", ["category"])
    op.create_index("ix_sms_messages_status", "sms_messages", ["status"])
    op.create_index("ix_sms_messages_student_id", "sms_messages", ["student_id"])


def downgrade():
    op.drop_index("ix_sms_messages_student_id", table_name="sms_messages")
    op.drop_index("ix_sms_messages_status", table_name="sms_messages")
    op.drop_index("ix_sms_messages_category", table_name="sms_messages")
    op.drop_index("ix_sms_messages_recipient", table_name="sms_messages")
    op.drop_table("sms_messages")
