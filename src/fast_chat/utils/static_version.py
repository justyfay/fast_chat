import hashlib
from functools import lru_cache
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent.parent / "templates" / "static"
VERSION_LENGTH = 10


def get_static_version() -> str:
    """Версия статики для адресов вида `/static/js/app.js?v=<версия>`."""
    signature = tuple(
        (path.relative_to(STATIC_DIR).as_posix(), stat.st_mtime_ns, stat.st_size)
        for path, stat in (
            (path, path.stat())
            for path in sorted(STATIC_DIR.rglob("*"))
            if path.is_file()
        )
    )
    return _version_by_signature(STATIC_DIR, signature)


@lru_cache(maxsize=4)
def _version_by_signature(
    static_dir: Path, signature: tuple[tuple[str, int, int], ...]
) -> str:
    digest = hashlib.sha1()
    for relative_path, _, _ in signature:
        digest.update(relative_path.encode())
        digest.update((static_dir / relative_path).read_bytes())
    return digest.hexdigest()[:VERSION_LENGTH]
