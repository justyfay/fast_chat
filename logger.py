import sys

from loguru import logger
from loguru._defaults import LOGURU_FORMAT  # noqa
from loguru._logger import Logger  # noqa

from config import settings


def get_logger() -> Logger:
    logger.configure(
        handlers=[
            {"sink": sys.stdout, "level": settings.log_level, "format": LOGURU_FORMAT}
        ]
    )
    return logger
