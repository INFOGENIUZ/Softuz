from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories import (
    get_user_by_telegram_id, toggle_favorite, is_favorite,
    get_user_favorites, get_program_by_id
)
from app.keyboards.inline_user import get_program_card_keyboard
from app.keyboards.reply import hide_reply_keyboard
from app.utils.paginator import Paginator
from app.utils.formatters import format_size, format_os, escape_text

router = Router(name="favorites_router")

@router.message(F.text == "⭐ Saqlanganlar")
async def msg_favorites(message: Message, session: AsyncSession):
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not user:
        await message.answer("Sizda hali saqlangan dasturlar mavjud emas.")
        return

    per_page = 5
    programs, total_count = await get_user_favorites(session, user.id, limit=per_page, offset=0)

    await hide_reply_keyboard(message)

    if total_count == 0:
        empty_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📂 Kategoriyalarni ko'rish", callback_data="open_categories")],
                [InlineKeyboardButton(text="🔙 Asosiy Menyu", callback_data="back_to_main")]
            ]
        )
        await message.answer(
            "⭐ <b>SAQLANGAN DASTURLAR RO'YXATI BO'SH</b>\n\n"
            "<i>Istalgan dastur kartochkasidagi «⭐ Saqlash» tugmasini bosib, uni o'zingizning xatcho'pingizga kiritib qo'yishingiz mumkin.</i>",
            reply_markup=empty_kb,
            parse_mode="HTML"
        )
        return

    paginator = Paginator(total_items=total_count, page=1, per_page=per_page)
    keyboard = []
    for p in programs:
        keyboard.append([
            InlineKeyboardButton(text=f"📦 {p.title} ({p.version})", callback_data=f"view_prog_{p.id}")
        ])

    nav_row = []
    if paginator.has_next:
        nav_row.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data="favpage_2"))
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton(text="🔙 Asosiy Menyu", callback_data="back_to_main")])

    text = f"⭐ <b>SIZNING SAQLANGAN DASTURLARINGIZ</b>\n\n<i>Jami saqlangan: {total_count} ta dastur</i>"
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")

@router.callback_query(F.data.startswith("favpage_"))
async def cb_favorites_page(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split("_")[1])
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.answer()
        return

    per_page = 5
    offset = (page - 1) * per_page
    programs, total_count = await get_user_favorites(session, user.id, limit=per_page, offset=offset)

    paginator = Paginator(total_items=total_count, page=page, per_page=per_page)
    keyboard = []
    for p in programs:
        keyboard.append([
            InlineKeyboardButton(text=f"📦 {p.title} ({p.version})", callback_data=f"view_prog_{p.id}")
        ])

    nav_row = []
    if paginator.has_prev:
        nav_row.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"favpage_{paginator.prev_page}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {paginator.page}/{paginator.total_pages}", callback_data="noop"))
    if paginator.has_next:
        nav_row.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"favpage_{paginator.next_page}"))
    keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton(text="🔙 Asosiy Menyu", callback_data="back_to_main")])

    text = f"⭐ <b>Siz saqlab qo'ygan dasturlar</b> (Jami: {total_count} ta):"
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("fav_"))
async def cb_toggle_favorite(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    prog_id = int(callback.data.split("_")[1])
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    prog = await get_program_by_id(session, prog_id)
    if not prog:
        await callback.answer("Dastur topilmadi!", show_alert=True)
        return

    added = await toggle_favorite(session, user.id, prog.id)
    bot_info = await bot.get_me()

    new_keyboard = get_program_card_keyboard(
        program_id=prog.id,
        file_size_formatted=format_size(prog.file_size),
        is_fav=added,
        bot_username=bot_info.username,
        prog_code=prog.code,
        back_target=f"cat_{prog.category_id}_1"
    )

    try:
        await callback.message.edit_reply_markup(reply_markup=new_keyboard)
    except Exception:
        pass

    if added:
        await callback.answer("❤️ Sevimlilarga qo'shildi!", show_alert=False)
    else:
        await callback.answer("🗑 Sevimlilardan olib tashlandi!", show_alert=False)
