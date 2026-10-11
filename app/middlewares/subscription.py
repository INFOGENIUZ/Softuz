from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.repositories import get_active_channels
from app.keyboards.inline_user import get_subscription_keyboard
from app.utils.cache import cache

class SubscriptionMiddleware(BaseMiddleware):
    """Homiy kanallarga a'zolikni tekshiruvchi tezkor keshli oraliq qatlam."""
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        session: AsyncSession = data.get("session")
        bot: Bot = data.get("bot")

        user_id = None
        is_callback = False
        callback_data = None

        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            text = event.text or ""
            if text.startswith("/admin"):
                return await handler(event, data)
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id
            is_callback = True
            callback_data = event.data

        # Agar admin bo'lsa yoki check_subscription tugmasi bosilgan bo'lsa o'tkazib yuboramiz
        if not user_id or user_id in settings.admin_ids or callback_data == "check_subscription":
            return await handler(event, data)

        # Agar foydalanuvchi obunasi keshda bo'lsa, hech qanday API so'rovisiz darhol o'tkazamiz
        if cache.is_user_subscribed(user_id):
            return await handler(event, data)

        if not session or not bot:
            return await handler(event, data)

        # Kanallarni keshdan tekshiramiz
        channels = cache.get_cached_channels()
        if channels is None:
            channels = await get_active_channels(session)
            cache.set_cached_channels(channels)

        if not channels:
            cache.mark_user_subscribed(user_id)
            return await handler(event, data)

        unsubscribed = []
        for ch in channels:
            try:
                member = await bot.get_chat_member(chat_id=ch.channel_id, user_id=user_id)
                if member.status in ["left", "kicked"]:
                    unsubscribed.append(ch)
            except Exception:
                # Agar bot kanalda admin bo'lmasa yoki kanal topilmasa xato bermasligi uchun
                continue

        if unsubscribed:
            cache.invalidate_user_subscription(user_id)
            text = (
                "⚠️ <b>Botdan foydalanish uchun quyidagi rasmiy kanallarga a'zo bo'lishingiz shart:</b>\n\n"
                "Iltimos, pastdagi havolalar orqali kanallarga kiring va <b>«🔄 A'zolikni tekshirish»</b> tugmasini bosing:"
            )
            keyboard = get_subscription_keyboard(unsubscribed)

            if is_callback:
                try:
                    await event.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
                except Exception:
                    pass
                await event.answer()
            else:
                await event.answer(text, reply_markup=keyboard, parse_mode="HTML")
            return None

        # Foydalanuvchi a'zo, keshga saqlaymiz (10 minut davomida qayta tekshirilmaydi)
        cache.mark_user_subscribed(user_id)
        return await handler(event, data)
