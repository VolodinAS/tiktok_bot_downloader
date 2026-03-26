import re

from aiogram.filters import BaseFilter
from aiogram.types import Message


class VideoLinkFilter(BaseFilter):
    """
    Фильтр проверяет, содержит ли сообщение ссылку на TikTok или YouTube Shorts.

    Поддерживаемые домены:
    - TikTok: tiktok.com, vm.tiktok.com, vt.tiktok.com, t.tiktok.com
    - YouTube Shorts: youtube.com/shorts/, youtu.be/shorts/, m.youtube.com/shorts/
    """
    
    TIKTOK_PATTERN = re.compile(
        r'https?://(www\.|vm\.|vt\.|t\.)?tiktok\.com/[^\s]+',
        re.IGNORECASE
    )
    
    YOUTUBE_SHORTS_PATTERN = re.compile(
        r'https?://(www\.|m\.)?youtube\.com/shorts/[^\s]+|https?://youtu\.be/[^\s]+',
        re.IGNORECASE
    )
    
    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False
        text = message.text.strip()
        return bool(
            self.TIKTOK_PATTERN.search(text) or
            self.YOUTUBE_SHORTS_PATTERN.search(text)
        )
