"""Persist risk experiment data separately from official academic records."""
from alembic import op
import sqlalchemy as sa

revision = 'e2b5d7f90103'
down_revision = 'd1a4c6e8f002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('risk_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('dataset_sha256', sa.String(64), nullable=False),
        sa.Column('student_key', sa.String(100), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('outcome_date', sa.Date(), nullable=False),
        sa.Column('prior_average', sa.Numeric(7,4), nullable=False),
        sa.Column('attendance_rate', sa.Numeric(7,6), nullable=False),
        sa.Column('early_average', sa.Numeric(7,4), nullable=False),
        sa.Column('credit_load', sa.Numeric(6,3), nullable=False),
        sa.Column('failed_later', sa.Boolean(), nullable=False),
        sa.Column('data_kind', sa.String(16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('dataset_sha256','student_key',name='uq_risk_dataset_student'),
        sa.CheckConstraint('outcome_date > snapshot_date',name='ck_risk_outcome_after_snapshot'),
        sa.CheckConstraint('prior_average BETWEEN 0 AND 100 AND early_average BETWEEN 0 AND 100',name='ck_risk_scores'),
        sa.CheckConstraint('attendance_rate BETWEEN 0 AND 1 AND credit_load BETWEEN 1 AND 40',name='ck_risk_inputs'),
        sa.CheckConstraint("data_kind IN ('synthetic','observed')",name='ck_risk_data_kind'))
    op.create_index('ix_risk_snapshots_dataset_sha256','risk_snapshots',['dataset_sha256'])
    op.create_table('risk_experiments',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('dataset_sha256',sa.String(64),unique=True,nullable=False),
        sa.Column('artifact',sa.JSON(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))


def downgrade():
    op.drop_table('risk_experiments')
    op.drop_table('risk_snapshots')
