from fastapi import (
    APIRouter,
    Request,
    Form,
    Depends,  # Depends не используется в этом файле, можно убрать, если он не нужен для других частей
    HTTPException,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.config import logger, TEMPLATES_DIR
from src.data_store import get_chat_id_by_code, get_chat_data

templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter()


@router.get("/", response_class=HTMLResponse, tags=["Auth"])
async def get_login_page(request: Request):
    """Serves the login page."""
    return templates.TemplateResponse(request=request, name="login.html")


@router.post("/login", tags=["Auth"])
async def login(
    request: Request, username: str = Form(...), access_code: str = Form(...)
):
    """Handles the login form submission."""
    clean_username = username.strip().lstrip("@")
    chat_id = get_chat_id_by_code(access_code)

    error_message = None
    login_success = False

    if chat_id:
        chat_info = get_chat_data(chat_id)
        if (
            chat_info
            and chat_info.get("access_code") == access_code
            and chat_info.get("username") == clean_username
        ):
            logger.info(f"Успешный вход для @{clean_username} (chat_id: {chat_id})")
            request.session["chat_id"] = chat_id
            request.session["username"] = clean_username
            login_success = True
        else:
            logger.warning(
                f"Неудачная попытка входа (данные не совпали): username='{clean_username}', code='{access_code}', chat_id={chat_id}, stored_user={chat_info.get('username') if chat_info else 'N/A'}, stored_code={chat_info.get('access_code') if chat_info else 'N/A'}"
            )
            error_message = (
                "Имя пользователя или код доступа не совпадают с активной сессией."
            )
    else:
        logger.warning(
            f"Неудачная попытка входа (код не найден): username='{clean_username}', code='{access_code}'"
        )
        error_message = "Неверный код доступа."

    if login_success:
        return RedirectResponse(url="/chat", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": error_message},
        )


@router.get("/logout", tags=["Auth"])
async def logout(request: Request):
    """Logs the user out by clearing the session."""
    chat_id = request.session.get("chat_id")
    logger.info(
        f"Пользователь выходит из веб-интерфейса (chat_id из сессии: {chat_id})."
    )
    request.session.clear()  # Важно: очистка сессии
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
