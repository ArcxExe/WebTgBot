import secrets
import asyncio
from datetime import datetime

from telegram import Bot
from telegram.ext import Application
from fastapi import (
    status,
    WebSocket,  # Используется для аннотаций типов
    WebSocketDisconnect,
)

from src.config import BOT_TOKEN, ACCESS_CODE_LENGTH, logger
from src.data_store import (
    chats_data,
    code_to_chat_id,
    active_websockets,  # Используется в stop_telegram_bot
    remove_active_websocket,
    get_active_websocket,
    clear_chat_session,
    add_message_to_store,
    # get_chat_id_by_code, # Этот импорт не используется в данном файле
    # set_chat_session, # Этот импорт не используется в данном файле
)

# --- Bot Initialization ---
telegram_bot = Bot(token=BOT_TOKEN)
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
            remove_active_websocket(chat_id)
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
    if chat_id not in chats_data:
        logger.warning(
            f"[add_message] Попытка добавить сообщение для не инициализированного chat_id: {chat_id}"
        )
        return False

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message_data = add_message_to_store(chat_id, sender, text, timestamp)

    if message_data:
        logger.info(
            f"[add_message] Сообщение добавлено для chat_id {chat_id}: {message_data}"
        )
        await notify_websocket_of_message(chat_id, message_data)
        return True
    else:
        logger.error(
            f"[add_message] Не удалось сохранить сообщение для chat_id {chat_id}"
        )
        return False


async def close_existing_session(chat_id: int) -> bool:
    """Closes an existing session for a chat_id."""
    logger.info(f"Попытка закрыть существующую сессию для chat_id: {chat_id}")
    chat_info = chats_data.get(chat_id)
    if not chat_info or not chat_info.get("access_code"):
        logger.info(f"Нет активной сессии для закрытия для chat_id: {chat_id}")
        return False

    old_code = chat_info["access_code"]
    clear_chat_session(chat_id)
    logger.info(
        f"Данные сессии (код доступа) очищены для chat_id: {chat_id}. Старый код: {old_code}"
    )

    websocket = remove_active_websocket(chat_id)
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
    return True


# --- Bot Lifecycle Management ---
async def run_telegram_bot():
    """Initializes handlers and starts the Telegram bot polling."""
    from src.bot.handlers import register_handlers

    logger.info("Регистрация обработчиков Telegram...")
    register_handlers(application)

    logger.info("Запуск Telegram Bot Polling...")
    try:
        await application.initialize()
        await application.start()
        # Проверка, что updater существует и не None перед вызовом start_polling
        if application.updater:
            await application.updater.start_polling(drop_pending_updates=True)
            logger.info("Telegram Bot Polling запущен.")
        else:
            logger.error("application.updater is None, cannot start polling.")
            # Можно пробросить исключение, если это критично
            # raise RuntimeError("Telegram bot updater not initialized.")
    except Exception as e:
        logger.error(f"Ошибка при запуске Telegram бота: {e}", exc_info=True)
        raise


async def stop_telegram_bot():
    """Stops the Telegram bot and closes active websockets."""
    logger.info("Остановка Telegram Bot Polling...")

    chat_ids = list(active_websockets.keys())
    for (
        chat_id_val
    ) in chat_ids:  # Изменено имя переменной, чтобы не конфликтовать с импортом
        ws = remove_active_websocket(chat_id_val)
        if ws:
            try:
                await ws.close(
                    code=status.WS_1001_GOING_AWAY, reason="Server shutting down"
                )
                logger.info(
                    f"WebSocket для chat_id {chat_id_val} закрыт при остановке сервера."
                )
            except Exception as e:
                logger.error(
                    f"Ошибка при закрытии WebSocket для chat_id {chat_id_val} при остановке: {e}"
                )

    if application.updater and application.updater.running:
        logger.info("Stopping Updater...")
        await application.updater.stop()
    logger.info("Stopping Application...")
    await application.stop()
    logger.info("Shutting down Application...")
    await application.shutdown()
    logger.info("Telegram Bot Polling остановлен.")
