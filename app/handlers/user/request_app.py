from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.repositories import get_user_by_telegram_id, create_app_request
from app.keyboards.inline_admin import get_request_actions_keyboard
from app.keyboards.reply import get_main_reply_keyboard, hide_reply_keyboard
from app.utils.formatters import escape_text

router = Router(name="request_app_router")

class RequestAppState(StatesGroup):
    waiting_app_name = State()

@router.message(F.text == "💡 Dastur so'rash")
async def msg_request_app(message: Message, state: FSMContext):
    await state.set_state(RequestAppState.waiting_app_name)
    await hide_reply_keyboard(message)
    text = (
        "💡 <b>DASTUR BUYURTMA QILISH (SO'ROV)</b>\n\n"
        "Sizga kerak bo'lgan dastur nomi, versiyasi va operatsion tizimini yozib yuboring:\n"
        "<i>Misol:</i> <code>AutoCAD 2024 Windows 64-bit</code>\n\n"
        "<blockquote>Biz uni imkon qadar tez topib, botga yuklaymiz!</blockquote>\n\n"
        "<i>Bekor qilish uchun pastdagi tugmani bosing:</i>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_request", style="danger")]]
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "start_request_app")
async def cb_start_request(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(RequestAppState.waiting_app_name)
    text = (
        "💡 <b>DASTUR BUYURTMA QILISH:</b>\n\n"
        "Sizga kerak bo'lgan dastur nomini va tizimini yozib yuboring (masalan: <i>CorelDRAW 2024 Windows</i>):"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_request")]]
    )
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "cancel_request")
async def cb_cancel_request(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    is_admin = callback.from_user.id in settings.admin_ids
    await callback.message.answer(
        "💡 <b>Dastur so'rash bekor qilindi.</b>\n👇 Asosiy menyudasiz:",
        reply_markup=get_main_reply_keyboard(is_admin=is_admin),
        parse_mode="HTML"
    )

@router.message(RequestAppState.waiting_app_name)
async def process_request_name(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    app_text = (message.text or "").strip()
    if len(app_text) < 3:
        await message.answer("⚠️ Iltimos, dastur nomini to'liqroq yozing:")
        return

    user = await get_user_by_telegram_id(session, message.from_user.id)
    user_id = user.id if user else 0

    req = await create_app_request(
        session=session,
        user_id=user_id,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        app_name=app_text
    )

    await state.clear()

    # Adminga bildirishnoma yuborish
    admin_text = (
        f"📩 <b>Yangi dastur buyurtmasi!</b> (ID: #{req.id})\n\n"
        f"📦 <b>Dastur:</b> {escape_text(app_text)}\n"
        f"👤 <b>Foydalanuvchi:</b> {escape_text(message.from_user.full_name)} "
        f"(@{message.from_user.username or 'yoq'}, ID: <code>{message.from_user.id}</code>)"
    )

    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                reply_markup=get_request_actions_keyboard(req.id),
                parse_mode="HTML"
            )
        except Exception:
            pass

    is_admin = message.from_user.id in settings.admin_ids
    await message.answer(
        "✅ <b>Rahmat! Buyurtmangiz qabul qilindi.</b>\n\n"
        "Administratorlar dasturni tekshirib, tez orada botga yuklashadi!",
        reply_markup=get_main_reply_keyboard(is_admin=is_admin),
        parse_mode="HTML"
    )
