"""drop is_admin from users

Revision ID: 267184b24b4d
Revises: 5005cacde9aa
Create Date: 2025-10-17 18:10:43.329628

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '267184b24b4d'
down_revision: Union[str, None] = '5005cacde9aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # If there are FKs, triggers, or indexes referencing is_admin (unlikely), drop them first.
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("is_admin")

def downgrade() -> None:
    # Recreate the column if you ever roll back
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    # Optional: remove default after backfill
    op.alter_column("users", "is_admin", server_default=None)
