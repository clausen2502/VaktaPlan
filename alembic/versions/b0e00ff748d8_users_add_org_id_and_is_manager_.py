"""users: add org_id and is_manager; (optional) migrate from org_members

Revision ID: b0e00ff748d8
Revises: 267184b24b4d
Create Date: 2025-10-23 17:09:08.880324

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# revision identifiers, used by Alembic.
revision: str = 'b0e00ff748d8'
down_revision: Union[str, None] = '267184b24b4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1) add columns to users
    op.add_column("users", sa.Column("org_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("is_manager", sa.Boolean(),
                                     server_default=sa.text("false"), nullable=False))
    op.create_index("ix_users_org_id", "users", ["org_id"])
    op.create_foreign_key(
        "fk_users_org_id_organizations",
        source_table="users",
        referent_table="organizations",
        local_cols=["org_id"],
        remote_cols=["id"],
        ondelete="RESTRICT",
    )

    # 2) backfill from org_members if present (best-effort)
    conn = op.get_bind()
    try:
        conn.execute(sa.text("""
            UPDATE users u
            SET org_id = s.org_id,
                is_manager = (s.role = 'manager')
            FROM (
                SELECT DISTINCT ON (user_id) user_id, org_id, role
                FROM org_members
                ORDER BY user_id,
                         CASE WHEN role='manager' THEN 0 ELSE 1 END
            ) AS s
            WHERE s.user_id = u.id AND u.org_id IS NULL
        """))
    except Exception:
        pass

    # 3) DO NOT set NOT NULL yet; we’ll do that in a later migration after verifying no NULLs
    # op.alter_column("users", "org_id", existing_type=sa.Integer(), nullable=False)

    # 4) drop org_members table if it exists
    inspector = sa_inspect(conn)
    if "org_members" in inspector.get_table_names():
        op.drop_table("org_members")

    # 5) drop enum type after the table is gone (Postgres only)
    # (use a DO block to “IF EXISTS” it without CASCADE)
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'member_role') THEN
            DROP TYPE member_role;
        END IF;
    END$$;
    """)

def downgrade():
    # Recreate member_role enum (Postgres)
    op.execute("CREATE TYPE member_role AS ENUM ('manager', 'employee')")

    # Recreate org_members table
    op.create_table(
        "org_members",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.Enum(name="member_role"), nullable=False, index=True),
        sa.Index("ix_org_members_org_id", "org_id"),
    )

    # Remove single-org columns
    op.drop_constraint("fk_users_org_id_organizations", "users", type_="foreignkey")
    op.drop_index("ix_users_org_id", table_name="users")
    op.drop_column("users", "is_manager")
    op.drop_column("users", "org_id")
