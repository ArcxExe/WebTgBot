import pytest
from httpx import AsyncClient
import httpx # Для использования httpx.codes

pytestmark = pytest.mark.asyncio


async def test_get_login_page(client: AsyncClient):
    """Тест: главная страница должна возвращать 200 OK и содержать форму входа."""
    response = await client.get("/")
    assert response.status_code == httpx.codes.OK
    content_str = response.content.decode("utf-8")
    assert '<form action="/login" method="post">' in content_str
    assert "Telegram Username" in content_str
    assert "Access Code" in content_str


async def test_successful_login(client: AsyncClient, setup_active_session):
    """Тест: успешный вход с правильными данными должен перенаправлять на /chat."""
    session_data = setup_active_session
    login_data = {
        "username": session_data["username"],
        "access_code": session_data["access_code"],
    }

    response = await client.post("/login", data=login_data, follow_redirects=False)

    assert response.status_code == httpx.codes.SEE_OTHER
    assert response.headers["location"] == "/chat"

    chat_response = await client.get(
        response.headers["location"]
    )
    assert chat_response.status_code == httpx.codes.OK
    assert (
        f'Chat with <span class="username-highlight">@{session_data["username"]}</span>'
        in chat_response.content.decode("utf-8")
    )


async def test_login_invalid_code(client: AsyncClient, setup_active_session):
    """Тест: вход с неверным кодом должен возвращать на страницу входа с ошибкой."""
    session_data = setup_active_session
    login_data = {"username": session_data["username"], "access_code": "wrongcode"}

    response = await client.post("/login", data=login_data, follow_redirects=False)

    assert response.status_code == httpx.codes.OK
    content_str = response.content.decode("utf-8")
    assert '<form action="/login" method="post">' in content_str
    assert "error-message" in content_str
    assert "Неверный код доступа" in content_str


async def test_login_code_ok_wrong_username(client: AsyncClient, setup_active_session):
    """Тест: вход с верным кодом, но неверным именем пользователя."""
    session_data = setup_active_session
    login_data = {"username": "wronguser", "access_code": session_data["access_code"]}

    response = await client.post("/login", data=login_data, follow_redirects=False)

    assert response.status_code == httpx.codes.OK
    content_str = response.content.decode("utf-8")
    assert '<form action="/login" method="post">' in content_str
    assert "error-message" in content_str
    assert "Имя пользователя или код доступа не совпадают" in content_str


async def test_logout(client: AsyncClient, setup_active_session):
    """Тест: выход из системы должен перенаправлять на главную страницу и очищать сессию."""
    session_data = setup_active_session
    login_data = {
        "username": session_data["username"],
        "access_code": session_data["access_code"],
    }

    initial_login_response = await client.post(
        "/login", data=login_data, follow_redirects=False
    )

    assert initial_login_response.status_code == httpx.codes.SEE_OTHER
    assert initial_login_response.headers["location"] == "/chat"

    chat_page_response = await client.get(initial_login_response.headers["location"])

    assert chat_page_response.status_code == httpx.codes.OK
    assert "/chat" in str(chat_page_response.url)
    assert (
        f'Chat with <span class="username-highlight">@{session_data["username"]}</span>'
        in chat_page_response.content.decode("utf-8")
    )

    logout_response = await client.get("/logout", follow_redirects=False)

    assert logout_response.status_code == httpx.codes.SEE_OTHER
    assert logout_response.headers["location"] == "/"

    chat_response_after_logout = await client.get("/chat", follow_redirects=False)
    assert chat_response_after_logout.status_code == httpx.codes.SEE_OTHER
    assert chat_response_after_logout.headers["location"] == "/"
