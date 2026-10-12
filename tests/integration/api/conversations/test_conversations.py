from async_asgi_testclient import TestClient
from fastapi import status

from ....constants import RoutersTestData
from ....utils.auth import UserData, register_user


async def test_conversations_list_is_empty_by_default(
    main_client: TestClient, user_one: UserData
) -> None:
    """У нового пользователя список бесед пуст"""
    # Act
    resp = await main_client.get(RoutersTestData.CONVERSATIONS_URL)

    # Assert
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == []


async def test_add_conversation_creates_record(
    main_client: TestClient, user_one: UserData, user_two: UserData
) -> None:
    """Добавление собеседника создаёт беседу"""
    # Act
    resp = await main_client.post(f"{RoutersTestData.CONVERSATIONS_URL}{user_two.id}")

    # Assert
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.json() == {"added": True, "recipient_id": user_two.id}
    partners = (await main_client.get(RoutersTestData.CONVERSATIONS_URL)).json()
    assert [partner["id"] for partner in partners] == [user_two.id]


async def test_error_add_conversation_twice(
    main_client: TestClient, user_one: UserData, user_two: UserData
) -> None:
    """Повторное добавление того же собеседника не создаёт дубликат"""
    # Arrange
    await main_client.post(f"{RoutersTestData.CONVERSATIONS_URL}{user_two.id}")

    # Act
    resp = await main_client.post(f"{RoutersTestData.CONVERSATIONS_URL}{user_two.id}")

    # Assert
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.json() == {"added": False, "recipient_id": user_two.id}
    assert len((await main_client.get(RoutersTestData.CONVERSATIONS_URL)).json()) == 1


async def test_error_add_conversation_with_yourself(
    main_client: TestClient, user_one: UserData
) -> None:
    """Нельзя добавить в беседы самого себя"""
    # Act
    resp = await main_client.post(f"{RoutersTestData.CONVERSATIONS_URL}{user_one.id}")

    # Assert
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


async def test_error_add_conversation_with_unknown_user(
    main_client: TestClient, user_one: UserData
) -> None:
    """Добавление несуществующего пользователя возвращает ошибку"""
    # Act
    resp = await main_client.post(f"{RoutersTestData.CONVERSATIONS_URL}999999")

    # Assert
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_conversation_is_one_directional(
    main_client: TestClient,
    other_client: TestClient,
    user_one: UserData,
    user_two: UserData,
) -> None:
    """Беседа односторонняя: у добавленного собеседника она не появляется"""
    # Arrange
    await main_client.post(f"{RoutersTestData.CONVERSATIONS_URL}{user_two.id}")

    # Act
    courtois_partners = (
        await other_client.get(RoutersTestData.CONVERSATIONS_URL)
    ).json()

    # Assert
    assert courtois_partners == []


async def test_delete_conversation_removes_record(
    main_client: TestClient, user_one: UserData, user_two: UserData
) -> None:
    """Удаление беседы убирает собеседника из списка"""
    # Arrange
    await main_client.post(f"{RoutersTestData.CONVERSATIONS_URL}{user_two.id}")

    # Act
    resp = await main_client.delete(f"{RoutersTestData.CONVERSATIONS_URL}{user_two.id}")

    # Assert
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {"deleted": True, "recipient_id": user_two.id}
    assert (await main_client.get(RoutersTestData.CONVERSATIONS_URL)).json() == []


async def test_error_delete_missing_conversation(
    main_client: TestClient, user_one: UserData, user_two: UserData
) -> None:
    """Удаление отсутствующей беседы возвращает ошибку"""
    # Act
    resp = await main_client.delete(f"{RoutersTestData.CONVERSATIONS_URL}{user_two.id}")

    # Assert
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_search_excludes_yourself_and_added_users(
    main_client: TestClient, user_one: UserData, user_two: UserData
) -> None:
    """Поиск не возвращает самого пользователя и уже добавленных собеседников"""
    # Arrange
    de_gea = await register_user(
        main_client, email="de.gea@example.com", full_name="David de Gea"
    )
    await main_client.post(f"{RoutersTestData.CONVERSATIONS_URL}{user_two.id}")

    # Act
    resp = await main_client.get(RoutersTestData.CONVERSATIONS_SEARCH_URL)

    # Assert
    assert resp.status_code == status.HTTP_200_OK
    assert [user["id"] for user in resp.json()] == [de_gea.id]


async def test_search_filters_by_name_case_insensitive(
    main_client: TestClient, user_one: UserData, user_two: UserData
) -> None:
    """Поиск фильтрует пользователей по имени без учёта регистра"""
    # Act
    resp = await main_client.get(
        RoutersTestData.CONVERSATIONS_SEARCH_URL, query_string={"q": "COURT"}
    )

    # Assert
    assert [user["id"] for user in resp.json()] == [user_two.id]


async def test_conversations_list_does_not_expose_hashed_password(
    main_client: TestClient, user_one: UserData, user_two: UserData
) -> None:
    """Список бесед не содержит хеш пароля собеседников"""
    # Arrange
    await main_client.post(f"{RoutersTestData.CONVERSATIONS_URL}{user_two.id}")

    # Act
    resp = await main_client.get(RoutersTestData.CONVERSATIONS_URL)

    # Assert
    assert resp.json()
    assert all("hashed_password" not in user for user in resp.json())


async def test_search_does_not_expose_hashed_password(
    main_client: TestClient, user_one: UserData, user_two: UserData
) -> None:
    """Результаты поиска бесед не содержат хеш пароля пользователей"""
    # Act
    resp = await main_client.get(RoutersTestData.CONVERSATIONS_SEARCH_URL)

    # Assert
    assert resp.json()
    assert all("hashed_password" not in user for user in resp.json())


async def test_conversations_without_cookie_redirects_to_login(
    main_client: TestClient,
) -> None:
    """Неавторизованный запрос списка бесед перенаправляет на страницу входа"""
    # Act
    resp = await main_client.get(
        RoutersTestData.CONVERSATIONS_URL, allow_redirects=False
    )

    # Assert
    assert resp.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert resp.headers["location"] == RoutersTestData.LOGIN_PAGE_URL
