"""Enforce one active enrollment per student and course offering.

The existing ``uq_enrollment_student_offering_status`` constraint prevents
exact duplicate statuses, but it still permits a student to have, for example,
one ``pending`` and one ``enrolled`` row for the same offering.  This partial
unique index enforces the business rule while preserving rejected/dropped
history rows.
"""

from alembic import op
import sqlalchemy as sa


revision = "b7c1a5f0d9e2"
down_revision = "a5dbe550ba23"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_active_enrollment_student_offering"
ACTIVE_STATUSES = ("pending", "enrolled", "completed")
ACTIVE_STATUS_SQL = "status IN ('pending', 'enrolled', 'completed')"


def upgrade() -> None:
    """Add the PostgreSQL partial unique index.

    Existing conflicting data is not deleted or silently changed.  The
    migration fails with an actionable error so an administrator can resolve
    the duplicate records intentionally before retrying the deployment.
    """
    bind = op.get_bind()
    conflicts = bind.execute(
        sa.text(
            """
            SELECT student_id, offering_id, COUNT(*) AS active_count
            FROM enrollments
            WHERE status IN ('pending', 'enrolled', 'completed')
            GROUP BY student_id, offering_id
            HAVING COUNT(*) > 1
            ORDER BY student_id, offering_id
            LIMIT 20
            """
        )
    ).fetchall()

    if conflicts:
        examples = ", ".join(
            f"student_id={student_id}, offering_id={offering_id}, count={active_count}"
            for student_id, offering_id, active_count in conflicts
        )
        raise RuntimeError(
            "Cannot create "
            f"{INDEX_NAME}: existing active enrollment conflicts found. "
            "Resolve duplicate pending/enrolled/completed records and rerun "
            f"the migration. Examples: {examples}"
        )

    op.create_index(
        INDEX_NAME,
        "enrollments",
        ["student_id", "offering_id"],
        unique=True,
        postgresql_where=sa.text(ACTIVE_STATUS_SQL),
    )


def downgrade() -> None:
    """Remove the partial unique index, retaining enrollment history."""
    op.drop_index(INDEX_NAME, table_name="enrollments")
