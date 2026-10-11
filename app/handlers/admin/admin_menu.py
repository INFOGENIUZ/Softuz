from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.core.config import settings
from app.keyboards.inline_admin import get_admin_main_menu
from app.keyboards.reply import get_main_reply_keyboard, hide_reply_keyboard

router = Router(name="admin_menu_router")

@router.message(Command("admin"))
@router.message(F.text == "🛠 Admin panel")
async def cmd_admin(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in settings.admin_ids:
        await message.answer(
            "⚠️ Ushbu bo'lim faqat administratorlar uchun mo'ljallangan.",
            reply_markup=get_main_reply_keyboard(is_admin=False)
        )
        return

    await hide_reply_keyboard(message)
    text = (
        "🛠 <b>ADMINISTRATOR BOSHQARUV PANELI</b>\n\n"
        "<blockquote>Bot statistikasi, yangi dastur kiritish, kanallar va sozlamalar:</blockquote>\n\n"
        "Kerakli bo'limni tanlang:"
    )
    await message.answer(text, reply_markup=get_admin_main_menu(), parse_mode="HTML")

@router.callback_query(F.data == "admin_menu")
async def cb_admin_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    if callback.from_user.id not in settings.admin_ids:
        return

    text = "🛠 <b>Admin Boshqaruv Paneli:</b>"
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_main_menu(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_admin_main_menu(), parse_mode="HTML")

@router.callback_query(F.data == "admin_close")
async def cb_admin_close(callback: CallbackQuery):
    await callback.answer("Admin panel yopildi.")
    try:
        await callback.message.delete()
    except Exception:
        pass
    is_admin = callback.from_user.id in settings.admin_ids
    await callback.message.answer(
        "👇 <b>Asosiy menyu:</b>",
        reply_markup=get_main_reply_keyboard(is_admin=is_admin),
        parse_mode="HTML"
    )
