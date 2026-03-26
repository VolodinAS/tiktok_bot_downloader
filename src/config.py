import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
VIDEOS_DIR = BASE_DIR / "videos" / "tik_tok"
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)


class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    VIDEOS_DIR: Path = VIDEOS_DIR
    # Максимальный размер видео в МБ (защита от переполнения диска)
    MAX_VIDEO_SIZE_MB: int = int(os.getenv("MAX_VIDEO_SIZE_MB", "50"))
    
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден в переменных окружения!")


config = Config()
