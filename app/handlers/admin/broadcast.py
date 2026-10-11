import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.repositories import get_all_active_user_ids, set_user_active_status

router = Router(name="broadcast_router")

class BroadcastState(StatesGroup):
    waiting_message = State()
    waiting_confirmation = State()

@router.callback_query(F.data == "admin_broadcast")
async def cb_start_broadcast(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.from_user.id not in settings.admin_ids:
        return

    await state.set_state(BroadcastState.waiting_message)
    text = (
        "📢 <b>Barcha foydalanuvchilarga xabar tarqatish:</b>\n\n"
        "Foydalanuvchilarga yuboriladigan xabarni (matn, rasm, video yoki post) yuboring:\n\n"
        "<i>Bekor qilish uchun pastdagi tugmani bosing:</i>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_menu")]]
    )
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.message(BroadcastState.waiting_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    await state.update_data(
        from_chat_id=message.chat.id,
        message_id=message.message_id
    )
    await state.set_state(BroadcastState.waiting_confirmation)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, yuborilsin!", callback_data="confirm_broadcast", style="success"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_menu", style="danger")
            ]
        ]
    )
    await message.reply(
        "❓ <b>Ushbu xabarni barcha faol foydalanuvchilarga tarqatishni tasdiqlaysizmi?</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@router.callback_query(BroadcastState.waiting_confirmation, F.data == "confirm_broadcast")
async def process_confirm_broadcast(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    await state.clear()

    from_chat_id = data["from_chat_id"]
    broadcast_msg_id = data["message_id"]

    user_ids = await get_all_active_user_ids(session)
    total_users = len(user_ids)

    if total_users == 0:
        await callback.message.answer("Tarqatish uchun foydalanuvchilar topilmadi.")
        return

    status_msg = await callback.message.answer(f"⏳ Xabar tarqatish boshlandi... Jami: {total_users} ta foydalanuvchi.")

    sent_count = 0
    blocked_count = 0
    error_count = 0

    for idx, user_id in enumerate(user_ids, 1):
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=from_chat_id,
                message_id=broadcast_msg_id
            )
            sent_count += 1
        except TelegramForbiddenError:
            # Bot foydalanuvchi tomonidan bloklangan
            blocked_count += 1
            await set_user_active_status(session, user_id, False)
        except Exception:
            error_count += 1

        # Har 50 ta xabarda progressni yangilash
        if idx % 50 == 0 or idx == total_users:
            try:
                await status_msg.edit_text(
                    f"📢 <b>Xabar tarqatilmoqda...</b>\n\n"
                    f"Progress: {idx}/{total_users} ({int(idx/total_users*100)}%)\n"
                    f"✅ Yetkazildi: {sent_count}\n"
                    f"🚫 Bloklagan: {blocked_count}\n"
                    f"❌ Xatolik: {error_count}",
                    parse_mode="HTML"
                )
            except Exception:
                pass

        # Telegram rate limits
        await asyncio.sleep(0.04)

    final_report = (
        "🎉 <b>Xabar tarqatish muvaffaqiyatli yakunlandi!</b>\n\n"
        f"👥 <b>Jami foydalanuvchilar:</b> {total_users}\n"
        f"✅ <b>Yetkazildi:</b> {sent_count}\n"
        f"🚫 <b>Botni bloklaganlar:</b> {blocked_count}\n"
        f"❌ <b>Xatolar:</b> {error_count}"
    )
    await callback.message.answer(final_report, parse_mode="HTML")
    await callback.answer("Tarqatish yakunlandi!", show_alert=True)
