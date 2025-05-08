import asyncio  # Добавлен импорт asyncio, если он не был выше
from contextlib import asynccontextmanager
from fastapi import (
    FastAPI,
    Request,
)  # Request может быть не нужен здесь, если не используется напрямую
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from src.config import (
    SESSION_SECRET_KEY,
    logger,
    STATIC_DIR,
    # TEMPLATES_DIR, # TEMPLATES_DIR импортируется в файлах роутов, здесь не обязателен
)

from src.bot.core import run_telegram_bot, stop_telegram_bot
from src.routes import auth, chat, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and shutdown events."""
    logger.info("Application startup via lifespan...")
    bot_task = None
    try:
        bot_task = asyncio.create_task(run_telegram_bot())
        await asyncio.sleep(0.1)
        if bot_task.done():
            exc = bot_task.exception()
            if exc:
                raise exc
        logger.info("Telegram bot startup task created and appears running.")
    except Exception as e:
        logger.error(f"Fatal error during Telegram bot startup: {e}", exc_info=True)
        # Решение о том, прерывать ли запуск приложения, зависит от критичности ошибки бота
        # Можно, например, `raise SystemExit("Failed to start critical bot component")`

    yield

    logger.info("Application shutdown via lifespan...")
    if bot_task and not bot_task.done():
        logger.info("Attempting to cancel bot task...")
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            logger.info("Bot task successfully cancelled.")
        except Exception as e:
            logger.error(f"Error waiting for cancelled bot task: {e}", exc_info=True)

    logger.info("Calling stop_telegram_bot()...")
    try:
        await stop_telegram_bot()
    except Exception as e:
        logger.error(f"Error during stop_telegram_bot: {e}", exc_info=True)

    logger.info("Application shutdown sequence complete.")


app = FastAPI(title="Telegram Web Chat Bridge", lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

try:
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    logger.info(f"Mounted static files from directory: {STATIC_DIR}")
except RuntimeError as e:
    logger.error(
        f"Failed to mount static files directory '{STATIC_DIR}': {e}. Please ensure it exists.",
        exc_info=True,
    )
    # Если статика критична, можно раскомментировать raise
    # raise

logger.info("Including routers...")
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(ws.router)
logger.info("Routers included.")


@app.get("/health", tags=["System"], summary="Perform a Health Check")
async def health_check():
    """Returns a simple status indicating the API is running."""
    return {"status": "ok"}
