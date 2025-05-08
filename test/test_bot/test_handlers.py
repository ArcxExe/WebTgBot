import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.bot.handlers import (
    start,
    handle_message,
    start_new_session,
    close_session_command,
)
from src.bot.keyboard import markup, SESSION_START_BUTTON, SESSION_CLOSE_BUTTON
from src.data_store import chats_data, code_to_chat_id

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_update():
    """Создает мок объекта Update с основными атрибутами."""
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 12345
    update.effective_user.username = "testuser"
    update.effective_user.full_name = "Test User"
    update.effective_chat = MagicMock()
    update.effective_chat.id = 12345
    update.message = AsyncMock()
    update.message.text = ""
    update.message.reply_html = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Создает мок объекта Context."""
    context = MagicMock()
    context.bot = AsyncMock()
    return context


async def test_start_new_user(mock_update, mock_context):
    """Тест: команда /start для нового пользователя генерирует код и отправляет приветствие."""
    await start(mock_update, mock_context)

    mock_update.message.reply_html.assert_called_once()
    call_args, call_kwargs = mock_update.message.reply_html.call_args
    assert "Привет, Test User!" in call_args[0]
    assert "Код доступа:" in call_args[0]
    assert "<code>" in call_args[0]
    assert call_kwargs["reply_markup"] == markup

    chat_id = mock_update.effective_chat.id
    assert chat_id in chats_data
    assert chats_data[chat_id]["username"] == "testuser"
    assert chats_data[chat_id]["access_code"] is not None
    access_code = chats_data[chat_id]["access_code"]
    assert access_code in code_to_chat_id
    assert code_to_chat_id[access_code] == chat_id


async def test_start_existing_user(mock_update, mock_context, setup_active_session):
    """Тест: команда /start для пользователя с активной сессией показывает существующий код."""
    session_data = setup_active_session
    mock_update.effective_chat.id = session_data["chat_id"]
    mock_update.effective_user.username = session_data["username"]
    # Если full_name также используется из session_data, его тоже нужно установить
    # mock_update.effective_user.full_name = "Имя из session_data"

    await start(mock_update, mock_context)

    mock_update.message.reply_html.assert_called_once()
    call_args, call_kwargs = mock_update.message.reply_html.call_args
    # Убедитесь, что имя пользователя в приветствии соответствует mock_update.effective_user.full_name
    assert "С возвращением, Test User!" in call_args[0] # или имя из session_data, если вы его мокируете
    assert f"Код доступа: <code>{session_data['access_code']}</code>" in call_args[0]
    assert call_kwargs["reply_markup"] == markup

    assert (
        chats_data[session_data["chat_id"]]["access_code"]
        == session_data["access_code"]
    )


async def test_handle_message_active_session(
    mock_update, mock_context, setup_active_session, mock_add_message
):
    """Тест: обработка сообщения от пользователя с активной сессией."""
    session_data = setup_active_session
    mock_update.effective_chat.id = session_data["chat_id"]
    mock_update.message.text = "Hello from user!"

    await handle_message(mock_update, mock_context)

    mock_add_message.assert_called_once_with(
        session_data["chat_id"], "user", "Hello from user!"
    )
    mock_update.message.reply_html.assert_not_called()


async def test_handle_message_no_session(mock_update, mock_context, mock_add_message):
    """Тест: обработка сообщения от пользователя без активной сессии."""
    mock_update.message.text = "Trying to chat"

    await handle_message(mock_update, mock_context)

    mock_add_message.assert_not_called()
    mock_update.message.reply_html.assert_called_once()
    call_args, call_kwargs = mock_update.message.reply_html.call_args
    assert "Пожалуйста, начните сессию" in call_args[0]
    assert call_kwargs["reply_markup"] == markup

# TODO: Добавьте тесты для start_new_session и close_session_command по аналогии,
# проверяя вызовы close_existing_session (который тоже можно мокировать),
# изменения в data_store и ответы пользователю.
