import hashlib
import logging
from pathlib import Path
from typing import Optional

import yt_dlp

from src.config import config


logger = logging.getLogger(__name__)


class VideoDownloadService:
    """Универсальный сервис для скачивания видео с TikTok и YouTube Shorts"""
    
    def __init__(self) -> None:
        self.videos_dir = config.VIDEOS_DIR
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = config.MAX_VIDEO_SIZE_MB * 1024 * 1024
    
    def _calculate_file_hash(self, filepath: Path) -> str:
        """Вычисляет SHA256 хэш файла для проверки на дубликаты"""
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
    
    def _get_platform_name(self, url: str) -> str:
        """Определяет платформу по URL для логирования"""
        if "tiktok.com" in url.lower():
            return "TikTok"
        if "youtube.com/shorts" in url.lower() or "youtu.be" in url.lower():
            return "YouTube Shorts"
        return "Unknown"
    
    def download_video(self, url: str) -> tuple[Optional[Path], Optional[str]]:
        """
        Скачивает видео с TikTok или YouTube Shorts.

        Returns:
            tuple[Optional[Path], Optional[str]]: (путь к файлу, сообщение об ошибке)
            Если успешно — ошибка None, если ошибка — путь None.
        """
        platform = self._get_platform_name(url)
        temp_name = f"temp_{url.replace('/', '_').replace(':', '_').replace('?', '_')[:40]}"
        output_template = str(self.videos_dir / temp_name)
        
        ydl_opts = {
            "format": "best[ext=mp4][height<=720]/best[ext=mp4]/best",
            "outtmpl": output_template + ".%(ext)s",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "socket_timeout": 30,
            "retries": 3,
            # YouTube-specific: игнорируем age-restricted для Shorts
            "age_limit": 0,
            # Ограничение по размеру файла (защита от гигантских видео)
            "max_filesize": self.max_file_size,
        }
        
        downloaded_path: Optional[Path] = None
        
        try:
            logger.info(f"📥 [{platform}] Начинаем скачивание: {url}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                if not info:
                    logger.error(f"[{platform}] yt-dlp вернул пустой info")
                    return None, f"❌ Не удалось получить информацию о видео ({platform})"
                
                logger.debug(f"[{platform}] yt-dlp info keys: {list(info.keys())[:8]}")
                
                # === Поиск пути к файлу (множественные стратегии) ===
                
                # Стратегия 1: ключ 'filepath'
                if (fp := info.get("filepath")) and isinstance(fp, str) and fp.strip():
                    candidate = Path(fp).resolve()
                    if candidate.is_file():
                        downloaded_path = candidate
                
                # Стратегия 2: ключ '_filename'
                if not downloaded_path and (fp := info.get("_filename")) and isinstance(fp, str):
                    candidate = Path(fp).resolve()
                    if candidate.is_file():
                        downloaded_path = candidate
                
                # Стратегия 3: ищем по video_id в папке
                if not downloaded_path and (video_id := info.get("id")):
                    for ext in [".mp4", ".webm", ".mkv", ".mov"]:
                        candidate = self.videos_dir / f"{video_id}{ext}"
                        if candidate.is_file():
                            downloaded_path = candidate
                            break
                
                # Стратегия 4: последний изменённый файл (fallback)
                if not downloaded_path:
                    mp4_files = [f for f in self.videos_dir.glob("*.mp4") if f.is_file()]
                    if mp4_files:
                        downloaded_path = max(mp4_files, key=lambda p: p.stat().st_mtime)
                
                # === Конец поиска ===
                
                if not downloaded_path:
                    logger.error(f"[{platform}] Не удалось определить путь к файлу")
                    return None, f"❌ Файл не был сохранён на диск ({platform})"
                
                if not downloaded_path.is_file():
                    logger.error(f"[{platform}] Путь существует, но это не файл: {downloaded_path}")
                    return None, f"❌ Ошибка: скачанный объект не является файлом ({platform})"
                
                # Проверка размера файла (дополнительная защита)
                if downloaded_path.stat().st_size > self.max_file_size:
                    logger.warning(
                        f"[{platform}] Файл превышает лимит: {downloaded_path.stat().st_size} байт"
                    )
                    downloaded_path.unlink(missing_ok=True)
                    return None, f"❌ Видео слишком большое (макс. {config.MAX_VIDEO_SIZE_MB} МБ)"
                
                logger.info(
                    f"[{platform}] ✅ Файл: {downloaded_path.name} ({downloaded_path.stat().st_size} байт)"
                )
                
                # Проверка на дубликаты
                try:
                    file_hash = self._calculate_file_hash(downloaded_path)
                    duplicate = self._find_duplicate(file_hash)
                    
                    if duplicate and duplicate != downloaded_path:
                        logger.info(f"[{platform}] ♻️ Найден дубликат: {duplicate.name}")
                        downloaded_path.unlink(missing_ok=True)
                        return duplicate, None
                except Exception as e:
                    logger.warning(f"[{platform}] ⚠️ Пропущена проверка дубликатов: {e}")
                
                return downloaded_path, None
        
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            logger.error(f"[{platform}] ❌ yt-dlp DownloadError: {error_msg[:200]}")
            
            if "Private video" in error_msg or "unavailable" in error_msg.lower():
                return None, f"❌ Видео недоступно или приватное ({platform})"
            if "age restricted" in error_msg.lower():
                return None, f"❌ Видео с возрастным ограничением ({platform})"
            if "Maximum file size" in error_msg:
                return None, f"❌ Видео слишком большое (макс. {config.MAX_VIDEO_SIZE_MB} МБ)"
            
            return None, f"❌ Ошибка скачивания: {error_msg[:120]}"
        
        except PermissionError as e:
            logger.exception(f"[{platform}] ❌ PermissionError: {e}")
            return None, f"❌ Ошибка доступа к файлу"
        
        except Exception as e:
            logger.exception(f"[{platform}] ❌ Неожиданная ошибка")
            return None, f"❌ Внутренняя ошибка: {str(e)[:100]}"


# Singleton instance
video_service = VideoDownloadService()
