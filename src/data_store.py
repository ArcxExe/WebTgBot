from collections import defaultdict  # Добавлен импорт defaultdict
from typing import Dict, List, Any, Optional
from fastapi import WebSocket  # Этот импорт нужен для аннотаций типов

chats_data: Dict[int, Dict[str, Any]] = defaultdict(
    lambda: {"username": None, "access_code": None, "messages": []}
)

code_to_chat_id: Dict[str, int] = {}

active_websockets: Dict[int, WebSocket] = {}


def get_chat_data(chat_id: int) -> Optional[Dict[str, Any]]:
    """Safely gets data for a chat_id."""
    return chats_data.get(chat_id)


def get_chat_id_by_code(access_code: str) -> Optional[int]:
    """Gets chat_id associated with an access code."""
    return code_to_chat_id.get(access_code)


def add_active_websocket(chat_id: int, websocket: WebSocket):
    """Registers an active websocket connection."""
    active_websockets[chat_id] = websocket


def remove_active_websocket(chat_id: int) -> Optional[WebSocket]:
    """Removes and returns a websocket connection."""
    return active_websockets.pop(chat_id, None)


def get_active_websocket(chat_id: int) -> Optional[WebSocket]:
    """Gets the active websocket for a chat_id."""
    return active_websockets.get(chat_id)


def clear_chat_session(chat_id: int):
    """Clears access code and potentially other session data for a chat."""
    if chat_id in chats_data:
        old_code = chats_data[chat_id].get("access_code")
        if old_code and old_code in code_to_chat_id:
            del code_to_chat_id[old_code]
        chats_data[chat_id]["access_code"] = None
        # Решение о сохранении/удалении истории сообщений остается за вами.
        # Если нужно удалять, раскомментируйте:
        # chats_data[chat_id]["messages"] = []
        # Или для полного удаления данных чата (если он больше не нужен):
        # del chats_data[chat_id]


def set_chat_session(chat_id: int, username: str, access_code: str):
    """Sets up a new chat session."""
    chats_data[chat_id]["username"] = username
    chats_data[chat_id]["access_code"] = access_code
    code_to_chat_id[access_code] = chat_id
    # По умолчанию сообщения не очищаются при установке новой сессии.
    # Если это нужно, раскомментируйте:
    # chats_data[chat_id]["messages"] = []


def add_message_to_store(
    chat_id: int, sender: str, text: str, timestamp: str
) -> Optional[Dict[str, str]]:  # Уточнил тип возвращаемого значения
    """Adds a message to the specific chat's message list."""
    if chat_id in chats_data:
        message_data = {"sender": sender, "text": text, "timestamp": timestamp}
        chats_data[chat_id]["messages"].append(message_data)
        return message_data
    return None  # Если chat_id не найден, возвращаем None


def get_messages(chat_id: int) -> List[Dict[str, Any]]:
    """Gets all messages for a chat."""
    return list(chats_data.get(chat_id, {}).get("messages", []))
