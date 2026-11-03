import pytest

from fast_chat.services.chat import ChatService
from fast_chat.services.message import MessageService

from ...utils.fakes import FakeChatDAO, FakeMessageDAO, FakeUserDAO


@pytest.fixture
async def users_dao() -> FakeUserDAO:
    dao = FakeUserDAO()
    await dao.add(full_name="Alisson Becker", email="alisson@example.com")
    await dao.add(full_name="Thibaut Courtois", email="courtois@example.com")
    await dao.add(full_name="David de Gea", email="de.gea@example.com")
    return dao


@pytest.fixture
def chats_dao(users_dao: FakeUserDAO) -> FakeChatDAO:
    return FakeChatDAO(users_dao)


@pytest.fixture
def chat_service(chats_dao: FakeChatDAO, users_dao: FakeUserDAO) -> ChatService:
    return ChatService(chats_dao, users_dao)  # type: ignore[arg-type]


@pytest.fixture
def messages_dao() -> FakeMessageDAO:
    return FakeMessageDAO()


@pytest.fixture
def message_service(
    messages_dao: FakeMessageDAO, chats_dao: FakeChatDAO, users_dao: FakeUserDAO
) -> MessageService:
    return MessageService(messages_dao, chats_dao, users_dao)  # type: ignore[arg-type]
