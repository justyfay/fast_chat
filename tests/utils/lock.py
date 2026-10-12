import fcntl
import re
import tempfile
from pathlib import Path
from typing import IO

from fast_chat.config import settings

_lock_file: IO | None = None


def get_lock_path() -> Path:
    """Файл блокировки привязан к серверу и имени тестовой БД, поэтому разные БД не мешают друг другу."""
    db_id = re.sub(
        r"\W+", "_", f"{settings.db_host}_{settings.db_port}_{settings.db_name}"
    )
    return Path(tempfile.gettempdir()) / f"fast_chat_tests_{db_id}.lock"


def try_acquire_test_db_lock() -> bool:
    """Занимает тестовую БД на время прогона. False, если её уже занял другой процесс.

    Блокировка снимается при завершении процесса, в том числе аварийном, поэтому
    «зависшей» блокировки после падения прогона не остаётся.
    """
    global _lock_file
    lock_file = get_lock_path().open("w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_file.close()
        return False
    _lock_file = lock_file
    return True


def release_test_db_lock() -> None:
    global _lock_file
    if _lock_file is not None:
        _lock_file.close()
        _lock_file = None
