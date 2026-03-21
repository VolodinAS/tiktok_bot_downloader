import re
from aiogram.filters import BaseFilter
from aiogram.types import Message

class TikTokLinkFilter(BaseFilter):
    """
    Фильтр проверяет, содержит ли сообщение ссылку на TikTok.
    Поддерживаем основные домены: tiktok.com, vm.tiktok.com, vt.tiktok.com
    """
    TIKTOK_PATTERN = re.compile(
        r'https?://(www\.|vm\.|vt\.|t\.)?tiktok\.com/[^\s]+',
        re.IGNORECASE
    )

    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False
        return bool(self.TIKTOK_PATTERN.search(message.text))