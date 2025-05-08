import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch

from src.app import app
from src.data_store import chats_data, code_to_chat_id, active_websockets
# from src.config import SESSION_SECRET_KEY # Не используется напрямую в этой фикстуре


@pytest_asyncio.fixture(scope="function")
async def client():
    """Фикстура для создания асинхронного HTTP клиента для тестов FastAPI."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        # Если вам нужно установить сессионные куки для тестов, делайте это здесь.
        # Однако, обычно SessionMiddleware должна корректно обрабатывать сессии
        # при использовании ASGITransport.
        # Пример: test_client.cookies.set("session", "some_test_session_id")
        yield test_client


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clear_data_stores():
    """Фикстура для очистки хранилищ данных до и после каждого теста."""
    chats_data.clear()
    code_to_chat_id.clear()
    active_websockets.clear()
    yield
    chats_data.clear()
    code_to_chat_id.clear()
    active_websockets.clear()


@pytest.fixture(scope="function")
def mock_telegram_bot(mocker):
    """Фикстура для мокирования объекта telegram.Bot."""
    mock_bot_instance = AsyncMock()
    mocker.patch("src.routes.chat.telegram_bot", mock_bot_instance, create=True)
    mocker.patch("src.bot.core.telegram_bot", mock_bot_instance, create=True)
    # Добавьте другие пути, если telegram_bot импортируется еще где-то
    return mock_bot_instance


@pytest.fixture(scope="function")
def mock_add_message(mocker):
    """Фикстура для мокирования функции add_message."""
    mock = mocker.patch("src.routes.chat.add_message", new_callable=AsyncMock)
    mocker.patch("src.bot.handlers.add_message", new=mock)
    mocker.patch("src.bot.core.add_message", new=mock)
    return mock


@pytest.fixture(scope="function")
def mock_notify_websocket(mocker):
    """Фикстура для мокирования функции notify_websocket_of_message."""
    return mocker.patch(
        "src.bot.core.notify_websocket_of_message", new_callable=AsyncMock
    )


@pytest.fixture(scope="function")
def setup_active_session():
    """Создает активную сессию в data_store для тестов."""
    test_chat_id = 12345
    test_username = "testuser"
    test_access_code = "testcode123"
    chats_data[test_chat_id] = {
        "username": test_username,
        "access_code": test_access_code,
        "messages": [],
    }
    code_to_chat_id[test_access_code] = test_chat_id
    return {
        "chat_id": test_chat_id,
        "username": test_username,
        "access_code": test_access_code,
    }


@pytest.fixture(scope="function")
def mock_websocket():
    """Создает мок WebSocket объекта."""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws
