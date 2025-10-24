"""users: make org_id NOT NULL

Revision ID: 8315c5e282b0
Revises: b0e00ff748d8
Create Date: 2025-10-23 17:18:40.644899

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8315c5e282b0'
down_revision: Union[str, None] = 'b0e00ff748d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "org_id", existing_type=sa.Integer(), nullable=False)



def downgrade() -> None:
    op.alter_column("users", "org_id", existing_type=sa.Integer(), nullable=True)

