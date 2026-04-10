"""add conversation table

Revision ID: a1b2c3d4e5f6
Revises: 2d3b0a9608d9
Create Date: 2025-01-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "2d3b0a9608d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("partner_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["partner_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "partner_id", name="uq_conversation_pair"),
    )
    op.create_index(op.f("ix_conversation_id"), "conversation", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_conversation_id"), table_name="conversation")
    op.drop_table("conversation")
