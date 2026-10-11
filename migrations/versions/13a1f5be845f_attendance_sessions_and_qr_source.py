"""attendance sessions and qr source

Revision ID: 13a1f5be845f
Revises: 0f6f7e1bddda
Create Date: 2026-10-12

Adds the ``attendance_sessions`` table and extends ``attendance`` with
``source`` and ``session_id`` for QR-code attendance (F3).
"""
from alembic import op
import sqlalchemy as sa


revision = '13a1f5be845f'
down_revision = '0f6f7e1bddda'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "attendance_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("offering_id", sa.Integer(), nullable=False),
        sa.Column("session_date", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("opened_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["offering_id"], ["course_offerings.id"],
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opened_by_id"], ["users.id"],
                                ondelete="SET NULL"),
        sa.UniqueConstraint("token", name="uq_attendance_session_token"),
    )
    op.create_index("ix_attendance_sessions_offering_id", "attendance_sessions",
                    ["offering_id"])
    op.create_index("ix_attendance_sessions_token", "attendance_sessions", ["token"])
    op.create_index("ix_attendance_sessions_is_open", "attendance_sessions", ["is_open"])

    op.add_column("attendance", sa.Column(
        "source", sa.String(length=8), nullable=False, server_default="manual"))
    op.add_column("attendance", sa.Column("session_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_attendance_session_id", "attendance", "attendance_sessions",
        ["session_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_attendance_session_id", "attendance", ["session_id"])


def downgrade():
    op.drop_index("ix_attendance_session_id", table_name="attendance")
    op.drop_constraint("fk_attendance_session_id", "attendance", type_="foreignkey")
    op.drop_column("attendance", "session_id")
    op.drop_column("attendance", "source")

    op.drop_index("ix_attendance_sessions_is_open", table_name="attendance_sessions")
    op.drop_index("ix_attendance_sessions_token", table_name="attendance_sessions")
    op.drop_index("ix_attendance_sessions_offering_id", table_name="attendance_sessions")
    op.drop_table("attendance_sessions")
