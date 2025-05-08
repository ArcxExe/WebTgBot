from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

from src.config import logger
from src.data_store import chats_data, set_chat_session, get_chat_data
from src.bot.core import (
    generate_access_code,
    close_existing_session,
    add_message,
    telegram_bot,
)
from src.bot.keyboard import (
    markup,
    SESSION_START_BUTTON,
    SESSION_CLOSE_BUTTON,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /start command. Sends greeting, generates code if needed, shows keyboard."""
    if not update.effective_user or not update.effective_chat:
        logger.warning("[start] Update is missing user or chat information.")
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    username = user.username or f"user_{user.id}"

    chat_info = get_chat_data(chat_id)
    access_code = chat_info.get("access_code") if chat_info else None

    if not access_code:
        logger.info(
            f"/start: Нет активной сессии для @{username} (chat_id: {chat_id}). Генерируем новую."
        )
        access_code = generate_access_code()
        set_chat_session(chat_id, username, access_code)
        logger.info(
            f"Сгенерирован код {access_code} для @{username} (chat_id: {chat_id})"
        )
        await add_message(chat_id, "system", f"Пользователь @{username} начал диалог.")

        message_text = (
            f"👋 Привет, {user.full_name}!\n\n"
            f"Я создал для вас сессию для подключения через веб-интерфейс:\n"
            f"Имя пользователя: <code>@{username}</code>\n"
            f"Код доступа: <code>{access_code}</code>\n\n"
            f"Используйте кнопки ниже для управления сессией."
        )
    else:
        chats_data[chat_id]["username"] = username
        logger.info(
            f"/start: Активная сессия уже существует для @{username} (chat_id: {chat_id}). Код: {access_code}"
        )
        message_text = (
            f"👋 С возвращением, {user.full_name}!\n\n"
            f"У вас уже есть активная сессия:\n"
            f"Имя пользователя: <code>@{username}</code>\n"
            f"Код доступа: <code>{access_code}</code>\n\n"
            f"Используйте кнопки ниже или введите сообщение для отправки оператору."
        )

    if update.message:
        await update.message.reply_html(message_text, reply_markup=markup)
    else:
        logger.warning(f"[start] No message found in update for chat_id {chat_id}")


async def start_new_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles 'Начать сессию / Новый код' button."""
    if not update.effective_user or not update.effective_chat:
        logger.warning(
            "[start_new_session] Update is missing user or chat information."
        )
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    username = user.username or f"user_{user.id}"

    logger.info(f"Запрос на новую сессию от @{username} (chat_id: {chat_id})")

    closed_old = await close_existing_session(chat_id)
    closed_message = "Предыдущая сессия (если была) закрыта.\n" if closed_old else ""

    access_code = generate_access_code()
    set_chat_session(chat_id, username, access_code)
    logger.info(
        f"Сгенерирован НОВЫЙ код {access_code} для @{username} (chat_id: {chat_id})"
    )
    await add_message(
        chat_id, "system", f"Пользователь @{username} запросил новую сессию."
    )

    message_text = (
        f"✅ {closed_message}"
        f"Создана новая сессия для подключения через веб-интерфейс:\n"
        f"Имя пользователя: <code>@{username}</code>\n"
        f"Код доступа: <code>{access_code}</code>"
    )

    if update.message:
        await update.message.reply_html(message_text, reply_markup=markup)
    else:
        logger.warning(
            f"[start_new_session] No message found in update for chat_id {chat_id}"
        )


async def close_session_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles 'Завершить сессию' button."""
    if not update.effective_user or not update.effective_chat:
        logger.warning(
            "[close_session_command] Update is missing user or chat information."
        )
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    username = user.username or f"user_{user.id}"

    logger.info(f"Запрос на завершение сессии от @{username} (chat_id: {chat_id})")

    closed = await close_existing_session(chat_id)

    if closed:
        message_text = "✅ Ваша текущая сессия и соединение с сайтом были завершены."
        await add_message(
            chat_id, "system", f"Пользователь @{username} завершил сессию."
        )
    else:
        message_text = "ℹ️ У вас нет активной сессии для завершения."

    if update.message:
        await update.message.reply_html(message_text, reply_markup=markup)
    else:
        logger.warning(
            f"[close_session_command] No message found in update for chat_id {chat_id}"
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles regular text messages from the user."""
    if (
        not update.effective_user
        or not update.effective_chat
        or not update.message
        or not update.message.text
    ):
        logger.warning(
            "[handle_message] Update missing required information (user, chat, message, text)."
        )
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    text = update.message.text
    chat_info = get_chat_data(chat_id)
    username = chat_info.get("username") if chat_info else None
    access_code = chat_info.get("access_code") if chat_info else None

    if not username or not access_code:
        logger.info(
            f"Сообщение от пользователя без активной сессии (chat_id: {chat_id}). Предлагаем начать."
        )
        await update.message.reply_html(
            "Пожалуйста, начните сессию с помощью команды /start или кнопки 'Начать сессию / Новый код', чтобы общаться с оператором.",
            reply_markup=markup,
        )
        return

    logger.info(f"Сообщение от @{username} (chat_id: {chat_id}): {text}")
    await add_message(chat_id, "user", text)


def register_handlers(application: Application):
    """Registers all handlers with the application."""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(f"^{SESSION_START_BUTTON}$"), start_new_session
        )
    )
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(f"^{SESSION_CLOSE_BUTTON}$"),
            close_session_command,
        )
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    logger.info("Обработчики Telegram успешно зарегистрированы.")
