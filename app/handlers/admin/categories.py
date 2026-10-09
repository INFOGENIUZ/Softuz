from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.repositories import get_all_categories, create_category, delete_category
from app.utils.formatters import escape_text

router = Router(name="admin_categories_router")

class AddCategoryState(StatesGroup):
    waiting_name = State()

@router.callback_query(F.data == "admin_cats")
async def cb_admin_categories(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("Ruxsat berilmagan!", show_alert=True)
        return

    categories = await get_all_categories(session, active_only=False)
    text = "🗂 <b>Kategoriyalarni boshqarish:</b>\n\n"
    keyboard = [
        [InlineKeyboardButton(text="➕ Yangi kategoriya qo'shish", callback_data="add_category", style="success")]
    ]

    for cat in categories:
        keyboard.append([
            InlineKeyboardButton(text=f"{cat.icon} {cat.name}", callback_data="noop", style="primary"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"delcat_{cat.id}", style="danger")
        ])

    keyboard.append([InlineKeyboardButton(text="🔙 Admin Menyusi", callback_data="admin_menu", style="danger")])

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "add_category")
async def cb_add_category_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddCategoryState.waiting_name)
    text = (
        "➕ <b>Yangi kategoriya nomini kiriting:</b>\n"
        "(Masalan: <code>📱 Android O'yinlar</code> yoki <code>🛡 VPN Utilitlar</code>):"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_cats", style="danger")]]
    )
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.message(AddCategoryState.waiting_name, F.text)
async def process_cat_name(message: Message, state: FSMContext, session: AsyncSession):
    cat_name = message.text.strip()
    if len(cat_name) < 2:
        await message.answer("⚠️ Kategoriya nomi juda qisqa:")
        return

    # Extract emoji if present at start or default to folder
    icon = "📁"
    await create_category(session, name=cat_name, icon=icon)
    await state.clear()

    await message.answer(f"✅ Kategoriya muvaffaqiyatli qo'shildi: <b>{escape_text(cat_name)}</b>", parse_mode="HTML")

@router.callback_query(F.data.startswith("delcat_"))
async def cb_delete_category(callback: CallbackQuery, session: AsyncSession):
    cat_id = int(callback.data.split("_")[1])
    await delete_category(session, cat_id)
    await callback.answer("🗑 Kategoriya o'chirildi!", show_alert=True)
    await cb_admin_categories(callback, session)
