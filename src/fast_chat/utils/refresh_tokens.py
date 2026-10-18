import hashlib
import json
import secrets
import time

from redis.asyncio import Redis

from fast_chat.config import settings
from fast_chat.constants import AuthData
from fast_chat.exceptions import RefreshRetryException, RefreshTokenInvalidException
from fast_chat.utils.token_revocation import check_redis_available, revoke_session


def _get_refresh_script() -> str:
    """
    Метод возвращает Lua-скрипт Redis, который за одну команду забирает старый refresh-токен,
    помечает его использованным и записывает новый. Если сессия уже отозвана, новый токен
    не выдаётся.
    """
    return """
        local record = redis.call('GET', KEYS[1])
        if not record then
          return nil
        end
        redis.call('DEL', KEYS[1])
        local sid = cjson.decode(record)['sid']
        if redis.call('EXISTS', ARGV[3] .. sid) == 1 then
          return nil
        end
        redis.call('SET', KEYS[2], ARGV[1] .. ' ' .. sid, 'EX', ARGV[2])
        redis.call('SET', KEYS[3], record, 'EX', ARGV[2])
        redis.call('SET', ARGV[4] .. sid, ARGV[5], 'EX', ARGV[2])
        return record
    """


def refresh_ttl() -> int:
    """Возвращает срок жизни refresh-токена в секундах."""
    return settings.refresh_token_expire_days * 24 * 60 * 60


def hash_token(token: str) -> str:
    """
    Метод возвращает SHA-256 хеш токена для хранения в Redis.

    :param token: Refresh-токен в открытом виде
    """
    return hashlib.sha256(token.encode()).hexdigest()


async def issue_refresh_token(redis: Redis, username: str, sid: str) -> str:
    """
    Метод выдаёт новый refresh-токен сессии. В Redis лежит только его хеш.

    :param redis: Экземпляр клиента Redis
    :param username: Имя пользователя, которому выдаётся токен
    :param sid: Идентификатор сессии
    """
    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)
    with check_redis_available():
        async with redis.pipeline(transaction=True) as pipe:
            pipe.set(
                AuthData.REFRESH_TOKEN_KEY.format(token_hash=token_hash),
                json.dumps({"sub": username, "sid": sid}),
                ex=refresh_ttl(),
            )
            pipe.set(
                AuthData.SESSION_REFRESH_KEY.format(sid=sid),
                token_hash,
                ex=refresh_ttl(),
            )
            await pipe.execute()
    return token


async def rotate_refresh_token(redis: Redis, token: str) -> tuple[str, str, str]:
    """Меняет refresh-токен на новый.

    Токен используется один раз. Повторное использование
    в течение времени указанного в `REFRESH_GRACE_SECONDS`
    считается гонкой, при привышении лимита - кражей.
    Для отозванной сессии новый токен не выдаётся.

    :param redis: Экземпляр клиента Redis
    :param token: Refresh-токен из cookie пользователя
    """
    token_hash = hash_token(token)
    new_token = secrets.token_urlsafe(32)
    new_hash = hash_token(new_token)
    with check_redis_available():
        record = await redis.eval(
            _get_refresh_script(),
            3,
            AuthData.REFRESH_TOKEN_KEY.format(token_hash=token_hash),
            AuthData.REFRESH_USED_KEY.format(token_hash=token_hash),
            AuthData.REFRESH_TOKEN_KEY.format(token_hash=new_hash),
            time.time(),
            refresh_ttl(),
            AuthData.REVOKED_SESSION_KEY.format(sid=""),
            AuthData.SESSION_REFRESH_KEY.format(sid=""),
            new_hash,
        )
        if record is None:
            used = await redis.get(
                AuthData.REFRESH_USED_KEY.format(token_hash=token_hash)
            )
            if used:
                used_at, sid = used.split(" ", 1)
                if time.time() - float(used_at) <= AuthData.REFRESH_GRACE_SECONDS:
                    raise RefreshRetryException
                await end_session(redis, sid)
            raise RefreshTokenInvalidException
    data = json.loads(record)
    return data["sub"], data["sid"], new_token


async def end_session(redis: Redis, sid: str) -> None:
    """
    Метод завершает сессию, отзывая access и refresh-токены.

    :param redis: Экземпляр клиента Redis
    :param sid: Идентификатор завершаемой сессии
    """
    await revoke_session(redis, sid)
    with check_redis_available():
        current_hash = await redis.getdel(AuthData.SESSION_REFRESH_KEY.format(sid=sid))
        if current_hash:
            await redis.delete(
                AuthData.REFRESH_TOKEN_KEY.format(token_hash=current_hash)
            )


async def get_refresh_session_id(redis: Redis, token: str) -> str | None:
    """
    Если refresh-токен известен, вернет sid сессии.

    :param redis: Экземпляр клиента Redis
    :param token: Refresh-токен из cookie пользователя
    """
    with check_redis_available():
        record = await redis.get(
            AuthData.REFRESH_TOKEN_KEY.format(token_hash=hash_token(token))
        )
    return json.loads(record)["sid"] if record else None
