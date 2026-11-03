from typing import Callable, Iterator

import pytest
from alembic import command
from alembic.config import Config

from ...utils.migrate import clear_data, get_alembic_config


@pytest.fixture
def schema_at(database_ready: None) -> Iterator[Callable[[str], Config]]:
    """
    Ставит схему тестовой БД на нужную ревизию и возвращает конфигурацию Alembic.
    После теста данные чистятся, а схема возвращается на `head`.
    """
    config = get_alembic_config()

    def set_revision(revision: str) -> Config:
        clear_data()
        command.downgrade(config, revision)
        return config

    try:
        yield set_revision
    finally:
        clear_data()
        command.upgrade(config, "head")
