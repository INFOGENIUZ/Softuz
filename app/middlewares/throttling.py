import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from app.core.config import settings

class ThrottlingMiddleware(BaseMiddleware):
    """Foydalanuvchilar botga spam qilmasligi uchun rate-limiting / anti-flood himoyasi."""
    def __init__(self, limit: float = 0.3):
        self.limit = limit
        self.user_timestamps: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id:
            # Adminlarni hech qachon cheklamaymiz
            if user_id in settings.admin_ids:
                return await handler(event, data)

            now = time.time()
            last_time = self.user_timestamps.get(user_id, 0.0)
            if now - last_time < self.limit:
                # Juda tez bosilganda
                if isinstance(event, CallbackQuery):
                    try:
                        await event.answer("⚠️ Iltimos, biroz kuting...", show_alert=False)
                    except Exception:
                        pass
                return None
            self.user_timestamps[user_id] = now

        return await handler(event, data)
