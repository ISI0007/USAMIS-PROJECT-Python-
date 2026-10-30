"""Track the avatar column through migrations instead of application startup.

Revision ID: d1a4c6e8f002
Revises: c9f2b7e4a1d3
"""
from alembic import op
import sqlalchemy as sa

revision = 'd1a4c6e8f002'
down_revision = 'c9f2b7e4a1d3'
branch_labels = None
depends_on = None


def upgrade():
    # Older releases added this column during startup. Preserve those installs.
    columns = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('users')}
    if 'avatar_path' not in columns:
        op.add_column('users', sa.Column('avatar_path', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('users', 'avatar_path')
