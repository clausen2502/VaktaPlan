"""Add schedules, link shifts, drop publications

Revision ID: d8f69a0ce087
Revises: ae712b9aa202
Create Date: 2025-10-27 15:38:37.868907
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d8f69a0ce087"
down_revision: Union[str, None] = "ae712b9aa202"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEDULE_ENUM = "schedule_status"
FK_SHIFTS_SCHEDULE = "fk_shifts_schedule_id_schedules"


def upgrade() -> None:
    # --- schedules (let SQLAlchemy auto-create the enum type) ---
    status_col = sa.Enum("draft", "published", name=SCHEDULE_ENUM)

    op.create_table(
        "schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("range_start", sa.Date(), nullable=False),
        sa.Column("range_end", sa.Date(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", status_col, nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id", "range_start", "range_end", "version", name="uq_schedule_range_version"
        ),
    )
    op.create_index(op.f("ix_schedules_created_by"), "schedules", ["created_by"], unique=False)
    op.create_index(op.f("ix_schedules_org_id"), "schedules", ["org_id"], unique=False)

    # --- drop publications if present (tolerant on dev DBs) ---
    for idx in ("ix_publications_org_id", "ix_publications_user_id"):
        try:
            op.drop_index(idx, table_name="publications")
        except Exception:
            pass
    try:
        op.drop_table("publications")
    except Exception:
        pass

    # --- shifts: add NOT NULL schedule_id, indexes, FK; drop old status column if present ---
    op.add_column("shifts", sa.Column("schedule_id", sa.Integer(), nullable=False))
    op.create_index(op.f("ix_shifts_schedule_id"), "shifts", ["schedule_id"], unique=False)
    op.create_index("ix_shifts_schedule_start", "shifts", ["schedule_id", "start_at"], unique=False)
    op.create_foreign_key(
        FK_SHIFTS_SCHEDULE, "shifts", "schedules", ["schedule_id"], ["id"], ondelete="CASCADE"
    )

    # drop shifts.status (old API) if it exists
    try:
        with op.batch_alter_table("shifts") as batch:
            batch.drop_column("status")
    except Exception:
        pass


def downgrade() -> None:
    # shifts: drop FK, indexes, column
    op.drop_constraint(FK_SHIFTS_SCHEDULE, "shifts", type_="foreignkey")
    op.drop_index("ix_shifts_schedule_start", table_name="shifts")
    op.drop_index(op.f("ix_shifts_schedule_id"), table_name="shifts")
    op.drop_column("shifts", "schedule_id")

    # schedules: drop unique/indexes/table
    op.drop_constraint("uq_schedule_range_version", "schedules", type_="unique")
    op.drop_index(op.f("ix_schedules_org_id"), table_name="schedules")
    op.drop_index(op.f("ix_schedules_created_by"), table_name="schedules")
    op.drop_table("schedules")

    # finally drop enum type (safe if it already exists)
    sa.Enum(name=SCHEDULE_ENUM).drop(op.get_bind(), checkfirst=True)
