import pytest

from fast_chat.config import Settings


@pytest.mark.parametrize(
    ("password", "expected_url"),
    [
        pytest.param("", "redis://redis:6379", id="without-password"),
        pytest.param("secret", "redis://:secret@redis:6379", id="simple-password"),
        pytest.param(
            "p@ss/word:1", "redis://:p%40ss%2Fword%3A1@redis:6379", id="special-chars"
        ),
    ],
)
def test_redis_url_includes_password(password: str, expected_url: str) -> None:
    """Адрес Redis содержит пароль в экранированном виде, если пароль задан"""
    # Arrange
    settings = Settings.model_construct(
        redis_host="redis", redis_port=6379, redis_password=password
    )

    # Act
    url = settings.redis_url

    # Assert
    assert url == expected_url
