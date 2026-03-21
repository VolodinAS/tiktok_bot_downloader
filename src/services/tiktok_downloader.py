import hashlib
import logging
from pathlib import Path
from typing import Optional

import yt_dlp

from src.config import config


logger = logging.getLogger(__name__)


class TikTokDownloadService:
    """Сервис для скачивания и обработки видео с TikTok"""
    
    def __init__(self) -> None:
        self.videos_dir = config.VIDEOS_DIR
        self.videos_dir.mkdir(parents=True, exist_ok=True)
    
    def _calculate_file_hash(self, filepath: Path) -> str:
        """Вычисляет SHA256 хэш файла для проверки на дубликаты"""
        # 🔒 Защита: проверяем, что это файл, а не директория
        if not filepath.is_file():
            logger.error(f"Попытка хэшировать не-файл: {filepath}")
            raise ValueError(f"Not a file: {filepath}")
        
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _find_duplicate(self, new_hash: str) -> Optional[Path]:
        """Ищет существующий файл с таким же хэшем"""
        for existing_file in self.videos_dir.glob("*.mp4"):
            try:
                if self._calculate_file_hash(existing_file) == new_hash:
                    return existing_file
            except (OSError, ValueError) as e:
                logger.warning(f"Пропущен файл при проверке дубликатов: {existing_file} ({e})")
                continue
        return None
    
    def download_video(self, url: str) -> tuple[Optional[Path], str]:
        """
        Скачивает видео с TikTok.
        Returns: (путь к файлу, сообщение статуса)
        """
        # Генерируем уникальное имя для временного файла
        temp_name = f"temp_{url.replace('/', '_').replace(':', '_')[:50]}"
        output_template = str(self.videos_dir / temp_name)
        
        ydl_opts = {
            "format": "best[ext=mp4]/best",
            "outtmpl": output_template + ".%(ext)s",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "socket_timeout": 30,
            "retries": 3,
        }
        
        downloaded_path: Optional[Path] = None
        
        try:
            logger.info(f"📥 Начинаем скачивание: {url}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                if not info:
                    logger.error("❌ yt-dlp вернул пустой info")
                    return None, "❌ Не удалось получить информацию о видео"
                
                # 🔍 Отладка: логируем ключи
                logger.debug(f"yt-dlp info keys: {list(info.keys())}")
                
                # === ПОИСК ПУТИ К ФАЙЛУ (множественные стратегии) ===
                
                # Стратегия 1: ключ 'filepath'
                if (fp := info.get("filepath")) and isinstance(fp, str) and fp.strip():
                    candidate = Path(fp).resolve()
                    if candidate.is_file():
                        downloaded_path = candidate
                        logger.debug(f"✓ Путь найден через 'filepath': {downloaded_path}")
                
                # Стратегия 2: ключ '_filename'
                if not downloaded_path and (fp := info.get("_filename")) and isinstance(fp, str):
                    candidate = Path(fp).resolve()
                    if candidate.is_file():
                        downloaded_path = candidate
                        logger.debug(f"✓ Путь найден через '_filename': {downloaded_path}")
                
                # Стратегия 3: ищем по шаблону в папке
                if not downloaded_path:
                    video_id = info.get("id", "")
                    if video_id:
                        for ext in [".mp4", ".webm", ".mkv", ".mov"]:
                            candidate = self.videos_dir / f"{video_id}{ext}"
                            if candidate.is_file():
                                downloaded_path = candidate
                                logger.debug(f"✓ Путь найден по video_id: {downloaded_path}")
                                break
                
                # Стратегия 4: ищем последний изменённый файл в папке (fallback)
                if not downloaded_path:
                    mp4_files = [f for f in self.videos_dir.glob("*.mp4") if f.is_file()]
                    if mp4_files:
                        downloaded_path = max(mp4_files, key=lambda p: p.stat().st_mtime)
                        logger.debug(f"✓ Путь найден как последний файл: {downloaded_path}")
                
                # === КОНЕЦ ПОИСКА ===
                
                if not downloaded_path:
                    logger.error(
                        f"❌ Не удалось определить путь к файлу. info keys: {list(info.keys())}"
                    )
                    return None, "❌ Файл не был сохранён на диск"
                
                # 🔒 Финальная защита: проверяем, что это действительно файл
                if not downloaded_path.is_file():
                    logger.error(f"❌ Путь существует, но это не файл: {downloaded_path}")
                    return None, "❌ Ошибка: скачанный объект не является файлом"
                
                logger.info(
                    f"✅ Файл определён: {downloaded_path} ({downloaded_path.stat().st_size} байт)"
                )
                
                # Проверка на дубликаты
                try:
                    file_hash = self._calculate_file_hash(downloaded_path)
                    duplicate = self._find_duplicate(file_hash)
                    
                    if duplicate and duplicate != downloaded_path:
                        logger.info(f"♻️ Найден дубликат: {duplicate.name}")
                        downloaded_path.unlink(missing_ok=True)
                        return duplicate, None
                except Exception as e:
                    logger.warning(f"⚠️ Пропущена проверка дубликатов: {e}")
                
                return downloaded_path, None
        
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            logger.error(f"❌ yt-dlp DownloadError: {error_msg}")
            if "Private video" in error_msg:
                return None, "❌ Видео приватное"
            if "unavailable" in error_msg.lower():
                return None, "❌ Видео недоступно"
            return None, f"❌ Ошибка скачивания: {error_msg[:150]}"
        except PermissionError as e:
            logger.exception(f"❌ PermissionError: {e}")
            return None, f"❌ Ошибка доступа к файлу: {str(e)[:100]}"
        except Exception as e:
            logger.exception(f"❌ Неожиданная ошибка")
            return None, f"❌ Внутренняя ошибка: {str(e)[:100]}"


# Singleton
tiktok_service = TikTokDownloadService()
