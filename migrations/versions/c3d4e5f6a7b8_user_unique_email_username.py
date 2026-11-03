"""unique indexes on lower(user.email) and lower(user.username)

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-03 00:00:00.000000

Миграция приводит `email` и `username` к нижнему регистру и создаёт уникальные индексы
по `lower(...)`. Если в таблице есть пользователи с одинаковым адресом без учёта регистра,
миграция останавливается, ничего не меняя: дубли нужно объединить или переименовать вручную.

Откат удаляет индексы. Прежний регистр букв в адресах восстановить нельзя,
поэтому приведение к нижнему регистру необратимо.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = ("email", "username")


def _find_duplicates(column: str) -> list[str]:
    """Возвращает адреса, повторяющиеся в колонке без учёта регистра, с числом повторов."""
    rows = (
        op.get_bind()
        .execute(
            sa.text(
                f'SELECT lower({column}), count(*) FROM "user" '
                f"GROUP BY lower({column}) HAVING count(*) > 1 ORDER BY 1"
            )
        )
        .fetchall()
    )
    return [f"{value} (x{count})" for value, count in rows]


def upgrade() -> None:
    for column in COLUMNS:
        duplicates = _find_duplicates(column)
        if duplicates:
            raise RuntimeError(
                f"Миграция остановлена: в user.{column} есть повторы без учёта регистра: "
                f"{', '.join(duplicates)}. Объедините или переименуйте дубли вручную "
                "и запустите миграцию снова."
            )

    op.execute('UPDATE "user" SET email = lower(email), username = lower(username)')
    for column in COLUMNS:
        op.create_index(
            f"uq_user_{column}_lower",
            "user",
            [sa.text(f"lower({column})")],
            unique=True,
        )


def downgrade() -> None:
    for column in COLUMNS:
        op.drop_index(f"uq_user_{column}_lower", table_name="user")
