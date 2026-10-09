from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.repositories import search_programs
from app.keyboards.inline_user import get_search_empty_keyboard
from app.keyboards.reply import get_main_reply_keyboard, hide_reply_keyboard
from app.utils.formatters import escape_text, format_os

router = Router(name="search_router")

class SearchState(StatesGroup):
    waiting_query = State()

@router.message(F.text == "🔍 Dastur qidirish")
async def msg_start_search(message: Message, state: FSMContext):
    await state.set_state(SearchState.waiting_query)
    await hide_reply_keyboard(message)
    text = (
        "🔍 <b>DASTURLARNI QIDIRISH TIZIMI</b>\n\n"
        "O'zingizga kerakli dastur nomini yozib yuboring:\n"
        "<i>Misol:</i> <code>Photoshop</code>, <code>Telegram</code>, <code>WinRAR</code>, <code>CapCut</code>...\n\n"
        "<i>Qidiruvni to'xtatish uchun pastdagi tugmani bosing:</i>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Qidiruvni bekor qilish", callback_data="cancel_search")]]
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "prompt_search")
async def cb_prompt_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchState.waiting_query)
    text = "🔍 <b>Qidirayotgan dastur nomini yozing:</b>"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_search")]]
    )
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "cancel_search")
async def cb_cancel_search(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    is_admin = callback.from_user.id in settings.admin_ids
    await callback.message.answer(
        "🔍 <b>Qidiruv bekor qilindi.</b>\n👇 Asosiy menyudasiz:",
        reply_markup=get_main_reply_keyboard(is_admin=is_admin),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(SearchState.waiting_query)
async def process_search_query(message: Message, state: FSMContext, session: AsyncSession):
    query = (message.text or "").strip()
    if len(query) < 2:
        await message.answer("⚠️ Iltimos, kamida 2 ta harfdan iborat nom kiriting:")
        return

    programs, total_count = await search_programs(session, query, limit=10)

    if total_count == 0:
        await state.clear()
        text = (
            f"❌ Afsuski, «<b>{escape_text(query)}</b>» so'rovi bo'yicha hech qanday dastur topilmadi.\n\n"
            f"Siz ushbu dasturni bot adminlariga buyurtma qilishingiz mumkin. Adminlar uni tez orada botga yuklab berishadi!"
        )
        await message.answer(text, reply_markup=get_search_empty_keyboard(), parse_mode="HTML")
        return

    await state.clear()
    text = f"🔎 «<b>{escape_text(query)}</b>» bo'yicha <b>{total_count} ta</b> natija topildi:\n\n"
    keyboard = []
    for idx, prog in enumerate(programs, 1):
        keyboard.append([
            InlineKeyboardButton(
                text=f"{idx}. {prog.title} ({prog.version}) - {format_os(prog.os_type)}",
                callback_data=f"view_prog_{prog.id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(text="🔍 Qayta qidirish", callback_data="prompt_search"),
        InlineKeyboardButton(text="🔙 Asosiy Menyu", callback_data="back_to_main")
    ])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
