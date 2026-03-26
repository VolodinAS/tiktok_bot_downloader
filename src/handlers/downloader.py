import asyncio
import logging

from aiogram import Router
from aiogram.types import FSInputFile, Message

from src.filters import VideoLinkFilter
from src.services.video_downloader import video_service


logger = logging.getLogger(__name__)
router = Router()


@router.message(VideoLinkFilter())
async def handle_video_link(message: Message) -> None:
    """Обрабатывает ссылку на TikTok или YouTube Shorts"""
    if not message.text:
        return
    
    url = message.text.strip()
    
    # 🔔 1. Сразу отправляем статус "В обработке"
    status_message = await message.answer("🎬 Видео взято в обработку...")
    
    # 🔽 2. Скачиваем в отдельном потоке (не блокируем event loop)
    video_path, error_msg = await asyncio.to_thread(
        video_service.download_video,
        url
    )
    
    # ❌ 3. Если ошибка — обновляем статус-сообщение
    if video_path is None:
        await status_message.edit_text(f"{error_msg}" if error_msg else "❌ Ошибка скачивания")
        return
    
    # ✅ 4. Отправляем видео (чистое, без капшена)
    try:
        video_file = FSInputFile(path=video_path)
        await message.answer_video(
            video=video_file,
            reply_to_message_id=message.message_id
        )
        
        # 🗑️ 5. Удаляем сообщение "В обработке" после успешной отправки
        await status_message.delete()
    
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")
        await status_message.edit_text("❌ Не удалось отправить видео")
    finally:
        # 🧹 6. Очищаем временный файл
        if video_path:
            video_path.unlink(missing_ok=True)


@router.message()
async def handle_unknown_command(message: Message) -> None:
    """Реагируем на любой другой контент"""
    await message.answer(
        "⚠️ Неизвестная команда. Пожалуйста, отправьте ссылку на TikTok или YouTube Shorts."
    )
