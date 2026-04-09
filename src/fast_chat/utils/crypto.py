import base64
import hashlib

from cryptography.fernet import Fernet

from config import settings


def _build_fernet() -> Fernet:
    """Метод создает Fernet-ключ из используя секретный ключ и алгоритм из env."""
    key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


_fernet = _build_fernet()


def encrypt(text: str) -> str:
    """Метод шифрует строку, возвращает base64-строку."""
    return _fernet.encrypt(text.encode()).decode()


def decrypt(token: str) -> str:
    """Метод дешифрует base64-строку. Если текст не зашифрован — возвращает как есть."""
    try:
        return _fernet.decrypt(token.encode()).decode()
    except Exception:
        return token
