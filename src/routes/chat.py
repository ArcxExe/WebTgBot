from fastapi import (
    APIRouter,
    Request,
    Form,
    Depends,
    HTTPException,  # Оставляем, так как может быть использован в будущем
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.config import logger, TEMPLATES_DIR
from src.data_store import get_chat_data, get_messages
from src.bot.core import telegram_bot, add_message

templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter(tags=["Chat"])


async def get_current_chat_session(
    request: Request,
) -> dict | RedirectResponse:  # Обновлен тип возвращаемого значения
    chat_id = request.session.get("chat_id")
    username = request.session.get("username")

    if not chat_id or not username:
        logger.warning("Доступ к чату без сессии. Редирект на /.")
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    chat_info = get_chat_data(chat_id)
    if not chat_info or not chat_info.get("access_code"):
        logger.warning(
            f"Доступ к /chat без активной серверной сессии (chat_id из сессии: {chat_id}). Очистка сессии и редирект на /."
        )
        request.session.clear()  # Важно: очистка сессии при невалидной серверной сессии
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    current_username = chat_info.get("username")
    if username != current_username:
        logger.info(
            f"Имя пользователя в сессии ('{username}') отличается от текущего ('{current_username}') для chat_id {chat_id}. Обновляем сессию."
        )
        request.session["username"] = current_username

    return {"chat_id": chat_id, "username": request.session["username"]}


@router.get("/chat", response_class=HTMLResponse)
async def get_chat_page(
    request: Request,
    session_data: dict | RedirectResponse = Depends(get_current_chat_session),
):
    """Serves the chat page if the user is authenticated."""
    if isinstance(session_data, RedirectResponse):
        return session_data

    chat_id = session_data["chat_id"]
    username = session_data["username"]
    messages = get_messages(chat_id)

    context = {
        "chat_id": chat_id,
        "username": username,
        "messages": messages,
    }
    return templates.TemplateResponse(
        request=request, name="chat.html", context=context
    )


@router.post("/send_message")
async def send_message_from_web(
    request: Request,
    message: str = Form(...),
    session_data: dict | RedirectResponse = Depends(get_current_chat_session),
):
    """Handles sending a message from the web interface to Telegram."""
    if isinstance(session_data, RedirectResponse):
        return session_data

    chat_id = session_data["chat_id"]

    if not message or not message.strip():
        return RedirectResponse(
            url="/chat?error=empty_message", status_code=status.HTTP_303_SEE_OTHER
        )

    try:
        logger.info(
            f"Отправка сообщения от админа в chat_id {chat_id}: {message[:50]}..."
        )
        await telegram_bot.send_message(chat_id=chat_id, text=message)
        await add_message(chat_id, "admin", message)

        return RedirectResponse(url="/chat", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        logger.error(f"Ошибка отправки сообщения в Telegram для chat_id {chat_id}: {e}")
        error_detail = f"Не удалось отправить сообщение: {e}"
        # По умолчанию возвращаем RedirectResponse с ошибкой
        return RedirectResponse(
            url=f"/chat?error={error_detail}", status_code=status.HTTP_303_SEE_OTHER
        )
        # Если вы предпочитаете HTTPException, раскомментируйте следующую строку
        # и закомментируйте RedirectResponse выше:
        # raise HTTPException(
        #     status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #     detail=error_detail,
        # )
