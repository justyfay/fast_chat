from typing import Any, Sequence

from loguru import logger
from sqlalchemy import RowMapping, Select, Result, select, insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.dml import ReturningInsert

from src.fast_chat.database import Base


class BaseDAO:
    model: type[Base] = None

    @classmethod
    async def find_one_or_none(
        cls, db_session: AsyncSession, **filter_by
    ) -> RowMapping | None:
        async with db_session as session:
            query: Select[tuple | Any] = select(cls.model.__table__.columns).filter_by(
                **filter_by
            )
            query_execute: Result[tuple | Any] = await session.execute(query)
            result: RowMapping | None = query_execute.mappings().one_or_none()
            logger.debug(f"Result: '{result}'")
            return result

    @classmethod
    async def find_all(
        cls, db_session: AsyncSession, **filter_by
    ) -> Sequence[RowMapping]:
        async with db_session as session:
            query: Select[tuple | Any] = select(cls.model.__table__.columns).filter_by(
                **filter_by
            )
            query_execute: Result[tuple | Any] = await session.execute(query)
            result: Sequence[RowMapping] = query_execute.mappings().all()
            logger.debug(f"Result: '{result}'")
            return result

    @classmethod
    async def add(cls, db_session: AsyncSession, **data) -> RowMapping | None | None:
        msg: str = ""
        try:
            query: ReturningInsert[tuple | Any] = (
                insert(cls.model).values(**data).returning(cls.model.id)  # noqa
            )
            async with db_session as session:
                query_execute: Result[tuple | Any] = await session.execute(query)
                result: RowMapping | None = query_execute.mappings().first()
                logger.debug(f"Result: '{result}'")
                await session.commit()
                return result
        except (SQLAlchemyError, Exception) as e:
            if isinstance(e, SQLAlchemyError):
                msg: str = (
                    "Database Exc: Cannot insert data into table. Details: {}".format(e)
                )
            elif isinstance(e, Exception):
                msg: str = (
                    "Unknown Exc: Cannot insert data into table. Details: {}".format(e)
                )

            logger.error(msg, extra={"table": cls.model.__tablename__}, exc_info=True)
            return None
