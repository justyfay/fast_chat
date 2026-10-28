import pytest

from fast_chat.services.conversation import ConversationService
from fast_chat.services.message import MessageService

from ...utils.fakes import FakeConversationDAO, FakeMessageDAO, FakeUserDAO


@pytest.fixture
async def users_dao() -> FakeUserDAO:
    dao = FakeUserDAO()
    await dao.add(full_name="Alisson Becker", email="alisson@example.com")
    await dao.add(full_name="Thibaut Courtois", email="courtois@example.com")
    await dao.add(full_name="David de Gea", email="de.gea@example.com")
    return dao


@pytest.fixture
def conversation_service(users_dao: FakeUserDAO) -> ConversationService:
    return ConversationService(FakeConversationDAO(users_dao), users_dao)  # type: ignore[arg-type]


@pytest.fixture
def messages_dao() -> FakeMessageDAO:
    return FakeMessageDAO()


@pytest.fixture
def message_service(messages_dao: FakeMessageDAO) -> MessageService:
    return MessageService(messages_dao)  # type: ignore[arg-type]
