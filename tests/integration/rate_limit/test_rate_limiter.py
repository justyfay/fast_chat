import pytest
from redis.asyncio import Redis

from fast_chat.dependencies.rate_limit import RateLimiter
from fast_chat.exceptions import TooManyRequests

from ...constants import RateLimitTestData


@pytest.fixture
def limiter() -> RateLimiter:
    return RateLimiter(
        RateLimitTestData.LIMITER_NAME,
        RateLimitTestData.ATTEMPTS,
        RateLimitTestData.INTERVAL_SECONDS,
    )


async def test_attempts_within_limit_are_allowed(
    limiter: RateLimiter, redis_connection: Redis
) -> None:
    """Попытки в пределах лимита проходят без ошибок"""
    # Act / Assert
    for _ in range(RateLimitTestData.ATTEMPTS):
        await limiter.check(redis_connection, RateLimitTestData.FIRST_IP)


async def test_error_attempt_over_limit_raises_too_many_requests(
    limiter: RateLimiter, redis_connection: Redis
) -> None:
    """При превышении лимита попыток возвращается ошибка 429,
    время ожидания не больше заданного интервала"""
    # Arrange
    for _ in range(RateLimitTestData.ATTEMPTS):
        await limiter.check(redis_connection, RateLimitTestData.FIRST_IP)

    # Act
    with pytest.raises(TooManyRequests) as exc_info:
        await limiter.check(redis_connection, RateLimitTestData.FIRST_IP)

    # Assert
    retry_after = int(exc_info.value.headers["Retry-After"])
    assert 1 <= retry_after <= RateLimitTestData.INTERVAL_SECONDS
    assert exc_info.value.status_code == 429


async def test_limit_is_counted_per_ip(
    limiter: RateLimiter, redis_connection: Redis
) -> None:
    """Исчерпанный лимит одного IP не мешает другому"""
    # Arrange
    for _ in range(RateLimitTestData.ATTEMPTS):
        await limiter.check(redis_connection, RateLimitTestData.FIRST_IP)

    # Act / Assert
    await limiter.check(redis_connection, RateLimitTestData.SECOND_IP)


async def test_counter_has_interval_ttl(
    limiter: RateLimiter, redis_connection: Redis
) -> None:
    """Лимит сбрасывается при истечении заданного интервала."""
    # Act
    await limiter.check(redis_connection, RateLimitTestData.FIRST_IP)

    # Assert
    ttl = await redis_connection.ttl(limiter.key(RateLimitTestData.FIRST_IP))
    assert 0 < ttl <= RateLimitTestData.INTERVAL_SECONDS


async def test_counter_without_ttl_gets_interval_ttl(
    limiter: RateLimiter, redis_connection: Redis
) -> None:
    """
    Ключ без срока жизни получает
    срок жизни интервала и не блокирует IP навсегда.
    """
    # Arrange
    key = limiter.key(RateLimitTestData.FIRST_IP)
    await redis_connection.set(key, 0)

    # Act
    await limiter.check(redis_connection, RateLimitTestData.FIRST_IP)

    # Assert
    ttl = await redis_connection.ttl(key)
    assert 0 < ttl <= RateLimitTestData.INTERVAL_SECONDS
