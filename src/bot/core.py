import secrets  # Добавьте этот импорт, если он отсутствует
import asyncio
from datetime import datetime  # Добавьте этот импорт, если он отсутствует

from telegram import Bot  # Добавьте этот импорт, если он отсутствует
from telegram.ext import Application
from fastapi import (
    status,
    WebSocket,  # Добавьте WebSocket, если он используется для аннотаций типов, иначе можно удалить
    WebSocketDisconnect,
)

from src.config import BOT_TOKEN, ACCESS_CODE_LENGTH, logger
from src.data_store import (
    chats_data,
    code_to_chat_id,  # Убедитесь, что используется, иначе можно удалить этот импорт
    active_websockets,
    remove_active_websocket,
    get_active_websocket,
    clear_chat_session,
    add_message_to_store,
)

# --- Bot Initialization ---
telegram_bot = Bot(token=BOT_TOKEN)
# Note: Building the application requires handlers, so we initialize later or pass handlers in.
# For simplicity, we'll build it fully in app.py after importing handlers.
application = Application.builder().token(BOT_TOKEN).build()


# --- Helper Functions ---
def generate_access_code() -> str:
    """Generates a secure random access code."""
    return secrets.token_hex(ACCESS_CODE_LENGTH // 2 + (ACCESS_CODE_LENGTH % 2))


async def notify_websocket_of_message(chat_id: int, message_data: dict):
    """Sends message data to the active websocket for the chat."""
    websocket = get_active_websocket(chat_id)
    if websocket:
        logger.info(
            f"[notify_websocket] Found active websocket for chat_id {chat_id}. Attempting to send: {message_data}"
        )
        try:
            await websocket.send_json(message_data)
            logger.info(
                f"[notify_websocket] Message successfully sent via WebSocket for chat_id {chat_id}"
            )
        except WebSocketDisconnect:
            logger.warning(
                f"[notify_websocket] WebSocket for chat_id {chat_id} disconnected before message send."
            )
            remove_active_websocket(chat_id)  # Clean up disconnected socket
        except Exception as e:
            logger.error(
                f"[notify_websocket] Error sending via WebSocket for chat_id {chat_id}: {e}"
            )
    else:
        logger.warning(
            f"[notify_websocket] No active websocket found for chat_id {chat_id} when trying to send message."
        )


async def add_message(chat_id: int, sender: str, text: str) -> bool:
    """Adds message to store and notifies WebSocket."""
    if chat_id not in chats_data:  # Check if chat exists (e.g., after /start)
        logger.warning(
            f"[add_message] Попытка добавить сообщение для не инициализированного chat_id: {chat_id}"
        )
        return False  # Добавлено для корректности

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message_data = add_message_to_store(chat_id, sender, text, timestamp)

    if message_data:
        logger.info(
            f"[add_message] Сообщение добавлено для chat_id {chat_id}: {message_data}"
        )
        await notify_websocket_of_message(chat_id, message_data)
        return True  # Добавлено для корректности
    else:
        logger.error(
            f"[add_message] Не удалось сохранить сообщение для chat_id {chat_id}"
        )
        return False  # Добавлено для корректности


async def close_existing_session(chat_id: int) -> bool:
    """Closes an existing session for a chat_id."""
    logger.info(f"Попытка закрыть существующую сессию для chat_id: {chat_id}")
    chat_info = chats_data.get(chat_id)
    if not chat_info or not chat_info.get("access_code"):
        logger.info(f"Нет активной сессии для закрытия для chat_id: {chat_id}")
        return False  # Добавлено для корректности

    old_code = chat_info["access_code"]  # Эта строка должна быть здесь
    clear_chat_session(
        chat_id
    )  # Clears code in chats_data and entry in code_to_chat_id
    logger.info(
        f"Данные сессии (код доступа) очищены для chat_id: {chat_id}. Старый код: {old_code}"
    )

    # Close active WebSocket
    websocket = remove_active_websocket(chat_id)  # Removes and gets the socket
    if websocket:
        try:
            await websocket.close(
                code=status.WS_1001_GOING_AWAY, reason="Session closed by user/system"
            )
            logger.info(f"Активный WebSocket для chat_id {chat_id} закрыт.")
        except Exception as e:
            logger.error(f"Ошибка при закрытии WebSocket для chat_id {chat_id}: {e}")
    else:
        logger.info(
            f"Активный WebSocket для chat_id {chat_id} не найден при закрытии сессии."
        )
    return True  # Добавлено для корректности


# --- Bot Lifecycle Management ---
async def run_telegram_bot():
    """Initializes handlers and starts the Telegram bot polling."""
    from src.bot.handlers import register_handlers  # Avoid circular import

    logger.info("Регистрация обработчиков Telegram...")
    register_handlers(application)  # Register handlers before starting

    logger.info("Запуск Telegram Bot Polling...")
    try:
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram Bot Polling запущен.")
    except Exception as e:
        logger.error(f"Ошибка при запуске Telegram бота: {e}", exc_info=True)
        # Consider re-raising or handling the exit more gracefully
        raise  # Добавлено для проброса исключения, если это нужно для lifespan


async def stop_telegram_bot():
    """Stops the Telegram bot and closes active websockets."""
    logger.info("Остановка Telegram Bot Polling...")

    # Close all active WebSockets gracefully
    chat_ids = list(active_websockets.keys())  # Copy keys as dict size may change
    for chat_id in chat_ids:
        ws = remove_active_websocket(chat_id)
        if ws:
            try:
                await ws.close(
                    code=status.WS_1001_GOING_AWAY, reason="Server shutting down"
                )
                logger.info(
                    f"WebSocket для chat_id {chat_id} закрыт при остановке сервера."
                )
            except Exception as e:
                logger.error(
                    f"Ошибка при закрытии WebSocket для chat_id {chat_id} при остановке: {e}"
                )

    # Stop the bot
    if application.updater and application.updater.running:
        logger.info("Stopping Updater...")
        await application.updater.stop()
    logger.info("Stopping Application...")
    await application.stop()
    logger.info("Shutting down Application...")
    await application.shutdown()
    logger.info("Telegram Bot Polling остановлен.")
