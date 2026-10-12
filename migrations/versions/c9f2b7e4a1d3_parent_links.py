"""parent links

Revision ID: c9f2b7e4a1d3
Revises: 13a1f5be845f
Create Date: 2026-10-12

Adds the ``parent_links`` table for the read-only parent portal (F5).
"""
from alembic import op
import sqlalchemy as sa


revision = 'c9f2b7e4a1d3'
down_revision = '13a1f5be845f'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "parent_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parent_user_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("relationship_type", sa.String(length=16), nullable=False,
                  server_default="guardian"),
        sa.Column("contact_phone", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["parent_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("parent_user_id", "student_id",
                            name="uq_parent_link_user_student"),
    )
    op.create_index("ix_parent_links_parent_user_id", "parent_links", ["parent_user_id"])
    op.create_index("ix_parent_links_student_id", "parent_links", ["student_id"])


def downgrade():
    op.drop_index("ix_parent_links_student_id", table_name="parent_links")
    op.drop_index("ix_parent_links_parent_user_id", table_name="parent_links")
    op.drop_table("parent_links")
