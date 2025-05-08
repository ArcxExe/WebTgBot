import os  # Добавлен импорт os
import logging  # Добавлен импорт logging
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in .env file")

SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")
if not SESSION_SECRET_KEY:
    # Используем print, так как логгер еще может быть не полностью настроен
    # или эта информация важна до инициализации логгера.
    print("Warning: SESSION_SECRET_KEY not found in .env. Using default (unsafe).")
    SESSION_SECRET_KEY = "your-super-secret-key-change-me"


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("app_logger")

# Предполагается, что этот файл (config.py) находится в папке src/
# Тогда BASE_DIR будет указывать на корень проекта (папку, содержащую src/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Если templates и static находятся ВНУТРИ src/:
# SRC_DIR = os.path.dirname(os.path.abspath(__file__))
# TEMPLATES_DIR = os.path.join(SRC_DIR, "templates")
# STATIC_DIR = os.path.join(SRC_DIR, "static")

# Если templates и static находятся В КОРНЕ ПРОЕКТА (на одном уровне с src/):
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")


ACCESS_CODE_LENGTH = 8
