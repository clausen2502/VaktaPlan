"""add active window to preferences

Revision ID: ae712b9aa202
Revises: 8315c5e282b0
Create Date: 2025-10-25 17:25:10.865652

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae712b9aa202'
down_revision: Union[str, None] = '8315c5e282b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("preferences", sa.Column("active_start", sa.Date(), nullable=True))
    op.add_column("preferences", sa.Column("active_end", sa.Date(), nullable=True))
    # NOT NULL with a temporary default so existing rows pass
    op.add_column(
        "preferences",
        sa.Column("do_not_schedule", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # Replace unique constraint to use do_not_schedule instead of is_negative
    op.drop_constraint("uq_preference_full", "preferences", type_="unique")
    op.create_unique_constraint(
        "uq_preference_full",
        "preferences",
        ["employee_id", "weekday", "start_time", "end_time", "do_not_schedule", "role_id", "location_id"],
    )

    # Remove old flag
    op.drop_column("preferences", "is_negative")

    # Make users.org_id nullable and keep a named FK
    op.alter_column("users", "org_id", existing_type=sa.INTEGER(), nullable=True)
    op.drop_constraint("fk_users_org_id_organizations", "users", type_="foreignkey")
    op.create_foreign_key(
        "fk_users_org_id_organizations",
        "users",
        "organizations",
        ["org_id"],
        ["id"],
    )

    # Drop the temporary default
    op.alter_column("preferences", "do_not_schedule", server_default=None)


def downgrade() -> None:
    # Users: restore strict FK and nullability
    op.drop_constraint("fk_users_org_id_organizations", "users", type_="foreignkey")
    op.create_foreign_key(
        "fk_users_org_id_organizations",
        "users",
        "organizations",
        ["org_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.alter_column("users", "org_id", existing_type=sa.INTEGER(), nullable=False)

    # Preferences: revert to is_negative, swap constraints back
    op.add_column("preferences", sa.Column("is_negative", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("preferences", "is_negative", server_default=None)

    op.drop_constraint("uq_preference_full", "preferences", type_="unique")
    op.create_unique_constraint(
        "uq_preference_full",
        "preferences",
        ["employee_id", "weekday", "start_time", "end_time", "is_negative", "role_id", "location_id"],
    )

    op.drop_column("preferences", "do_not_schedule")
    op.drop_column("preferences", "active_end")
    op.drop_column("preferences", "active_start")
