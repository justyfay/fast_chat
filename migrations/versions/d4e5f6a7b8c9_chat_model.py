"""chat model: chat, chat_member, message.chat_id and created_at

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-11-03 00:00:00.000000

Миграция данных: для каждой пары пользователей, у которой есть беседа (`conversation`)
или сообщения, создаётся личный чат с обоими участниками, сообщения привязываются к нему.
Таблица `conversation` и колонка `message.recipient_id` удаляются.
Старые сообщения не имели времени, их `created_at` равен моменту миграции,
порядок сохраняется по `id`.

Откат восстанавливает `conversation` и `message.recipient_id` из чатов. Он невозможен,
если появились чаты не личного типа (группы и каналы): их нельзя выразить старой схемой.
Время сообщений при откате теряется.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Ключ личного чата пары: «меньший id:больший id»
PAIR_KEY = "least({a}, {b})::text || ':' || greatest({a}, {b})::text"


def upgrade() -> None:
    op.create_table(
        "chat",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(16), server_default="direct", nullable=False),
        sa.Column("direct_key", sa.String(32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("direct_key"),
    )
    op.create_table(
        "chat_member",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chat_id"], ["chat.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_id", "user_id", name="uq_chat_member"),
    )
    op.create_index("ix_chat_member_user_id", "chat_member", ["user_id"])

    op.add_column("message", sa.Column("chat_id", sa.Integer(), nullable=True))
    op.add_column(
        "message",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.execute(
        f"""
        INSERT INTO chat (type, direct_key)
        SELECT 'direct', {PAIR_KEY.format(a="a", b="b")}
        FROM (
            SELECT user_id AS a, recipient_id AS b FROM conversation
            UNION
            SELECT sender_id, recipient_id FROM message
        ) AS pairs
        GROUP BY 2
        """
    )
    op.execute(
        """
        INSERT INTO chat_member (chat_id, user_id)
        SELECT c.id, unnest(string_to_array(c.direct_key, ':')::int[])
        FROM chat c
        ON CONFLICT DO NOTHING
        """
    )
    op.execute(
        f"""
        UPDATE message m SET chat_id = c.id
        FROM chat c
        WHERE c.direct_key = {PAIR_KEY.format(a="m.sender_id", b="m.recipient_id")}
        """
    )

    op.alter_column("message", "chat_id", nullable=False)
    op.create_foreign_key(
        "message_chat_id_fkey",
        "message",
        "chat",
        ["chat_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_message_chat_id_id", "message", ["chat_id", "id"])
    op.drop_column("message", "recipient_id")
    op.drop_index("ix_conversation_id", table_name="conversation")
    op.drop_table("conversation")


def downgrade() -> None:
    not_direct = op.get_bind().execute(
        sa.text("SELECT count(*) FROM chat WHERE type <> 'direct'")
    )
    if not_direct.scalar():
        raise RuntimeError(
            "Откат остановлен: в БД есть чаты не личного типа (группы или каналы), "
            "старая схема их не хранит. Удалите их вручную и повторите откат."
        )

    op.create_table(
        "conversation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("recipient_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["recipient_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "recipient_id", name="uq_conversation_pair"),
    )
    op.create_index("ix_conversation_id", "conversation", ["id"], unique=False)
    op.execute(
        """
        INSERT INTO conversation (user_id, recipient_id)
        SELECT cm.user_id,
               CASE WHEN split_part(c.direct_key, ':', 1)::int = cm.user_id
                    THEN split_part(c.direct_key, ':', 2)::int
                    ELSE split_part(c.direct_key, ':', 1)::int END
        FROM chat_member cm JOIN chat c ON c.id = cm.chat_id
        WHERE split_part(c.direct_key, ':', 1) <> split_part(c.direct_key, ':', 2)
        ORDER BY cm.id
        """
    )

    op.add_column("message", sa.Column("recipient_id", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE message m SET recipient_id =
            CASE WHEN split_part(c.direct_key, ':', 1)::int = m.sender_id
                 THEN split_part(c.direct_key, ':', 2)::int
                 ELSE split_part(c.direct_key, ':', 1)::int END
        FROM chat c WHERE c.id = m.chat_id
        """
    )
    op.alter_column("message", "recipient_id", nullable=False)
    op.create_foreign_key(
        "message_recipient_id_fkey", "message", "user", ["recipient_id"], ["id"]
    )

    op.drop_index("ix_message_chat_id_id", table_name="message")
    op.drop_constraint("message_chat_id_fkey", "message", type_="foreignkey")
    op.drop_column("message", "created_at")
    op.drop_column("message", "chat_id")
    op.drop_index("ix_chat_member_user_id", table_name="chat_member")
    op.drop_table("chat_member")
    op.drop_table("chat")
