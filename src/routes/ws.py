from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    status,
    Depends,
    HTTPException,  # Оставляем на случай будущего использования
    Request,
)

from src.config import logger
from src.data_store import (
    add_active_websocket,
    remove_active_websocket,
    get_chat_data,
)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


async def validate_websocket_session(websocket: WebSocket, client_chat_id: int) -> int:
    """
    Validates the WebSocket connection against the browser session
    and server-side chat data. Returns the validated chat_id.
    Relies on SessionMiddleware being active.
    """
    try:
        session_chat_id = websocket.session.get("chat_id")

        if not session_chat_id:
            logger.warning("WebSocket: Отказ. Нет chat_id в сессии браузера.")
            raise WebSocketDisconnect(
                code=status.WS_1008_POLICY_VIOLATION, reason="No session found"
            )

        if session_chat_id != client_chat_id:
            logger.warning(
                f"WebSocket: Отказ. ID сессии ({session_chat_id}) не совпадает с ID в URL ({client_chat_id})"
            )
            raise WebSocketDisconnect(
                code=status.WS_1008_POLICY_VIOLATION, reason="Session ID mismatch"
            )

        chat_info = get_chat_data(client_chat_id)
        if not chat_info or not chat_info.get("access_code"):
            logger.warning(
                f"WebSocket: Отказ. Сессия для chat_id {client_chat_id} не активна в chats_data."
            )
            raise WebSocketDisconnect(
                code=status.WS_1008_POLICY_VIOLATION, reason="Session not active"
            )

        return client_chat_id

    except AttributeError as e:
        logger.error(
            f"WebSocket: Ошибка доступа к websocket.session: {e}. Убедитесь, что SessionMiddleware настроена правильно.",
            exc_info=True,
        )
        raise WebSocketDisconnect(
            code=status.WS_1011_INTERNAL_ERROR, reason="Server configuration error"
        )
    except WebSocketDisconnect as wsd:
        # Re-raise WebSocketDisconnect exceptions to let FastAPI handle them
        raise wsd  # Важно: повторно вызываем исключение
    except Exception as e:
        logger.error(
            f"WebSocket: Неожиданная ошибка валидации для chat_id {client_chat_id}: {e}",
            exc_info=True,
        )
        raise WebSocketDisconnect(
            code=status.WS_1011_INTERNAL_ERROR, reason="Validation error"
        )


@router.websocket("/{client_chat_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_chat_id: int = Depends(validate_websocket_session),
):
    """Handles WebSocket connections for real-time updates."""
    await websocket.accept()
    logger.info(f"WebSocket: Установлено соединение для chat_id: {client_chat_id}")
    add_active_websocket(client_chat_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(
                f"WebSocket: Получено от клиента {client_chat_id}: {data} (игнорируется)"
            )

    except WebSocketDisconnect as e:
        logger.info(
            f"WebSocket: Соединение закрыто для chat_id: {client_chat_id}. Код: {e.code}, Причина: {e.reason}"
        )
    except Exception as e:
        logger.error(
            f"WebSocket: Неожиданная ошибка для chat_id {client_chat_id}: {e}",
            exc_info=True,
        )
    finally:
        removed_socket = remove_active_websocket(client_chat_id)
        if removed_socket:
            logger.info(
                f"WebSocket: Запись об активном соединении для chat_id {client_chat_id} удалена."
            )
        else:
            logger.warning(
                f"WebSocket: Попытка удалить запись для chat_id {client_chat_id}, но она уже отсутствовала."
            )
