"""Preserve fractional credits and allow the seeded 15-credit thesis."""
from alembic import op
import sqlalchemy as sa

revision='f3c6e8a01204'
down_revision='e2b5d7f90103'
branch_labels=None
depends_on=None


def upgrade():
    op.drop_constraint('ck_course_credits_range','courses',type_='check')
    op.alter_column('courses','credits',existing_type=sa.Integer(),type_=sa.Numeric(5,2),postgresql_using='credits::numeric(5,2)')
    op.create_check_constraint('ck_course_credits_range','courses','credits > 0 AND credits <= 20')


def downgrade():
    # Do not silently truncate fractional or >12-credit academic records.
    connection=op.get_bind()
    if connection.execute(sa.text('SELECT count(*) FROM courses WHERE credits <> trunc(credits) OR credits > 12')).scalar():
        raise RuntimeError('Cannot downgrade while fractional or above-12 credits exist.')
    op.drop_constraint('ck_course_credits_range','courses',type_='check')
    op.alter_column('courses','credits',existing_type=sa.Numeric(5,2),type_=sa.Integer(),postgresql_using='credits::integer')
    op.create_check_constraint('ck_course_credits_range','courses','credits > 0 AND credits <= 12')
