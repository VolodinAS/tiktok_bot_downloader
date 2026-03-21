import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
VIDEOS_DIR = BASE_DIR / "videos" / "tik_tok"

# Создаем папку при инициализации
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)


class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    VIDEOS_DIR: Path = VIDEOS_DIR
    
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден в переменных окружения!")


config = Config()
