from sqlalchemy.ext.asyncio import AsyncSession
import pytest

from fast_chat.dao.user import UserDAO


@pytest.mark.parametrize(
    "field",
    [
        pytest.param("hashed_password", id="hashed-password"),
        pytest.param("full_name", id="full-name"),
        pytest.param("telegram_unic_code", id="telegram"),
    ],
)
async def test_error_find_user_by_forbidden_field(
    field: str, db_session: AsyncSession
) -> None:
    """Подбор пользователя по закрытой колонке (например, хешу пароля) невозможен."""
    # Act / Assert
    with pytest.raises(ValueError, match=field):
        await UserDAO(db_session).find_one_or_none(**{field: "x"})
