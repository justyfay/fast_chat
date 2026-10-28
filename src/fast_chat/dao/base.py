from typing import Any, ClassVar, Sequence

from loguru import logger
from sqlalchemy import RowMapping, Select, Result, select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.dml import ReturningInsert

from fast_chat.database import Base


class BaseDAO:
    """Базовый класс работы с таблицами.

    :cvar model: Модель таблицы
    :cvar filterable_fields: Колонки, по которым разрешён поиск через `**filter_by`
    """

    model: type[Base] = None
    filterable_fields: ClassVar[frozenset[str]] = frozenset()

    def __init__(self, session: AsyncSession) -> None:
        """
        :param session: Сессия БД текущей транзакции
        """
        self.session = session

    def _check_filter(self, filter_by: dict[str, Any]) -> None:
        """
        Не даёт искать по колонкам, не входящим в `filterable_fields`.

        :param filter_by: Условия поиска «колонка: значение»
        """
        forbidden = set(filter_by) - self.filterable_fields
        if forbidden:
            raise ValueError(
                f"[{self.model.__tablename__}] поиск по полям {sorted(forbidden)} запрещён"
            )

    async def find_one_or_none(self, **filter_by) -> RowMapping | None:
        self._check_filter(filter_by)
        query: Select[tuple | Any] = select(self.model.__table__.columns).filter_by(
            **filter_by
        )
        query_execute: Result[tuple | Any] = await self.session.execute(query)
        result: RowMapping | None = query_execute.mappings().one_or_none()
        logger.debug(
            f"[{self.model.__tablename__}] find_one_or_none: found={result is not None}"
        )
        return result

    async def find_all(self, **filter_by) -> Sequence[RowMapping]:
        self._check_filter(filter_by)
        query: Select[tuple | Any] = select(self.model.__table__.columns).filter_by(
            **filter_by
        )
        query_execute: Result[tuple | Any] = await self.session.execute(query)
        result: Sequence[RowMapping] = query_execute.mappings().all()
        logger.debug(f"[{self.model.__tablename__}] find_all: count={len(result)}")
        return result

    async def add(self, **data) -> RowMapping:
        """Добавляет запись, возвращает её `id`. Ошибки БД не перехватываются."""
        query: ReturningInsert[tuple | Any] = (
            insert(self.model).values(**data).returning(self.model.id)  # noqa
        )
        query_execute: Result[tuple | Any] = await self.session.execute(query)
        result: RowMapping = query_execute.mappings().one()
        logger.debug(f"[{self.model.__tablename__}] add: id={result['id']}")
        return result
