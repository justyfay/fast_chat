from async_asgi_testclient import TestClient
from fastapi import status

from ....constants import RoutersTestData
from ....utils.auth import UserData, register_user


async def test_chats_list_is_empty_by_default(
    main_client: TestClient, user_one: UserData
) -> None:
    """У нового пользователя список чатов пуст"""
    # Act
    resp = await main_client.get(RoutersTestData.CONVERSATIONS_URL)

    # Assert
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == []


async def test_add_chat_creates_record(
    main_client: TestClient, user_one: UserData, user_two: UserData
) -> None:
    """Добавление собеседника создаёт чат"""
    # Act
    resp = await main_client.post(f"{RoutersTestData.CONVERSATIONS_URL}{user_two.id}")

    # Assert
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.json() == {"added": True, "recipient_id": user_two.id}
    partners = (await main_client.get(RoutersTestData.CONVERSATIONS_URL)).json()
    assert [partner["id"] for partner in partners] == [user_two.id]


async def test_error_add_chat_twice(
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


async def test_error_add_chat_with_yourself(
    main_client: TestClient, user_one: UserData
) -> None:
    """Нельзя добавить в чаты самого себя"""
    # Act
    resp = await main_client.post(f"{RoutersTestData.CONVERSATIONS_URL}{user_one.id}")

    # Assert
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


async def test_error_add_chat_with_unknown_user(
    main_client: TestClient, user_one: UserData
) -> None:
    """Добавление несуществующего пользователя возвращает ошибку"""
    # Act
    resp = await main_client.post(f"{RoutersTestData.CONVERSATIONS_URL}999999")

    # Assert
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_chat_is_visible_to_both_users(
    main_client: TestClient,
    other_client: TestClient,
    user_one: UserData,
    user_two: UserData,
) -> None:
    """Чат общий: у добавленного собеседника он появляется тоже"""
    # Arrange
    await main_client.post(f"{RoutersTestData.CONVERSATIONS_URL}{user_two.id}")

    # Act
    courtois_partners = (
        await other_client.get(RoutersTestData.CONVERSATIONS_URL)
    ).json()

    # Assert
    assert [partner["id"] for partner in courtois_partners] == [user_one.id]


async def test_delete_chat_keeps_it_for_partner(
    main_client: TestClient,
    other_client: TestClient,
    user_one: UserData,
    user_two: UserData,
) -> None:
    """Удаление чата убирает его только из своего списка, у собеседника он остаётся"""
    # Arrange
    await main_client.post(f"{RoutersTestData.CONVERSATIONS_URL}{user_two.id}")

    # Act
    await main_client.delete(f"{RoutersTestData.CONVERSATIONS_URL}{user_two.id}")

    # Assert
    courtois_partners = (
        await other_client.get(RoutersTestData.CONVERSATIONS_URL)
    ).json()
    assert [partner["id"] for partner in courtois_partners] == [user_one.id]


async def test_new_message_returns_deleted_chat_to_list(
    main_client: TestClient,
    other_client: TestClient,
    user_one: UserData,
    user_two: UserData,
) -> None:
    """Новое сообщение возвращает в список чат, который пользователь ранее убрал, с историей"""
    # Arrange
    await main_client.post(f"{RoutersTestData.CONVERSATIONS_URL}{user_two.id}")
    await main_client.delete(f"{RoutersTestData.CONVERSATIONS_URL}{user_two.id}")

    # Act
    await other_client.post(
        RoutersTestData.MESSAGES_SEND_URL,
        json={"recipient_id": user_one.id, "body": "вернись"},
    )

    # Assert
    partners = (await main_client.get(RoutersTestData.CONVERSATIONS_URL)).json()
    assert [partner["id"] for partner in partners] == [user_two.id]


async def test_delete_chat_removes_record(
    main_client: TestClient, user_one: UserData, user_two: UserData
) -> None:
    """Удаление чата убирает собеседника из списка"""
    # Arrange
    await main_client.post(f"{RoutersTestData.CONVERSATIONS_URL}{user_two.id}")

    # Act
    resp = await main_client.delete(f"{RoutersTestData.CONVERSATIONS_URL}{user_two.id}")

    # Assert
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {"deleted": True, "recipient_id": user_two.id}
    assert (await main_client.get(RoutersTestData.CONVERSATIONS_URL)).json() == []


async def test_error_delete_missing_chat(
    main_client: TestClient, user_one: UserData, user_two: UserData
) -> None:
    """Удаление отсутствующего чата возвращает ошибку"""
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


async def test_chats_list_does_not_expose_hashed_password(
    main_client: TestClient, user_one: UserData, user_two: UserData
) -> None:
    """Список чатов не содержит хеш пароля собеседников"""
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
    """Результаты поиска чатов не содержат хеш пароля пользователей"""
    # Act
    resp = await main_client.get(RoutersTestData.CONVERSATIONS_SEARCH_URL)

    # Assert
    assert resp.json()
    assert all("hashed_password" not in user for user in resp.json())


async def test_chats_without_cookie_redirects_to_login(
    main_client: TestClient,
) -> None:
    """Неавторизованный запрос списка чатов перенаправляет на страницу входа"""
    # Act
    resp = await main_client.get(
        RoutersTestData.CONVERSATIONS_URL, allow_redirects=False
    )

    # Assert
    assert resp.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert resp.headers["location"] == RoutersTestData.LOGIN_PAGE_URL
