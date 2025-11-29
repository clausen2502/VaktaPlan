"""add schedule name

Revision ID: 1fa129643119
Revises: 41f0f779f959
Create Date: 2025-11-29 14:09:02.149963

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1fa129643119'
down_revision: Union[str, None] = '41f0f779f959'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1) add as nullable first
    op.add_column(
        "schedules",
        sa.Column("name", sa.String(length=200), nullable=True),
    )

    # 2) backfill existing rows with some reasonable default
    #    you can change this text to whatever you want
    op.execute(
        """
        UPDATE schedules
        SET name = CONCAT(
            'Plan ',
            range_start::text,
            ' – ',
            range_end::text,
            ' v', version::text
        )
        WHERE name IS NULL
        """
    )

    # 3) now enforce NOT NULL
    op.alter_column("schedules", "name", nullable=False)


def downgrade():
    op.drop_column("schedules", "name")
