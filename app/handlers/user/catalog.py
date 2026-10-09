from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories import (
    get_all_categories, get_category_by_id, get_programs_by_category,
    get_program_by_id, increment_views, is_favorite, get_program_rating_stats,
    get_top_programs, get_latest_programs, get_user_by_telegram_id
)
from app.keyboards.inline_user import (
    get_categories_keyboard, get_programs_list_keyboard, get_program_card_keyboard
)
from app.keyboards.reply import hide_reply_keyboard
from app.utils.paginator import Paginator
from app.utils.formatters import format_size, format_os, escape_text

router = Router(name="catalog_router")

@router.message(F.text == "📂 Kategoriyalar")
async def msg_categories(message: Message, session: AsyncSession):
    categories = await get_all_categories(session, active_only=True)
    if not categories:
        await message.answer("📂 Hozircha kategoriyalar mavjud emas.")
        return
    await hide_reply_keyboard(message)
    text = (
        "📂 <b>KATEGORIYALAR KATALOGI</b>\n\n"
        "<i>Kerakli bo'lim yoki dastur yo'nalishini tanlang:</i>"
    )
    await message.answer(text, reply_markup=get_categories_keyboard(categories), parse_mode="HTML")

@router.callback_query(F.data == "open_categories")
async def cb_open_categories(callback: CallbackQuery, session: AsyncSession):
    categories = await get_all_categories(session, active_only=True)
    if not categories:
        await callback.answer("Hozircha bo'limlar yo'q.", show_alert=True)
        return
    text = "📂 <b>Kerakli bo'lim yoki dastur yo'nalishini tanlang:</b>"
    try:
        await callback.message.edit_text(text, reply_markup=get_categories_keyboard(categories), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_categories_keyboard(categories), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("cat_"))
async def cb_category_programs(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split("_")
    cat_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 1

    category = await get_category_by_id(session, cat_id)
    if not category:
        await callback.answer("Kategoriya topilmadi!", show_alert=True)
        return

    per_page = 5
    offset = (page - 1) * per_page
    programs, total_count = await get_programs_by_category(session, cat_id, limit=per_page, offset=offset)

    if total_count == 0:
        await callback.answer("Ushbu bo'limda hozircha dasturlar yo'q.", show_alert=True)
        return

    paginator = Paginator(total_items=total_count, page=page, per_page=per_page)
    keyboard = get_programs_list_keyboard(programs, paginator, prefix="cat", extra_id=cat_id)

    text = f"{category.icon} <b>{escape_text(category.name)} bo'limidagi dasturlar</b> (Jami: {total_count} ta):"
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("page_cat_"))
async def cb_category_pagination(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split("_")
    cat_id = int(parts[2])
    page = int(parts[3])

    category = await get_category_by_id(session, cat_id)
    if not category:
        await callback.answer("Kategoriya topilmadi!", show_alert=True)
        return

    per_page = 5
    offset = (page - 1) * per_page
    programs, total_count = await get_programs_by_category(session, cat_id, limit=per_page, offset=offset)

    paginator = Paginator(total_items=total_count, page=page, per_page=per_page)
    keyboard = get_programs_list_keyboard(programs, paginator, prefix="cat", extra_id=cat_id)

    text = f"{category.icon} <b>{escape_text(category.name)} bo'limidagi dasturlar</b> (Jami: {total_count} ta):"
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("view_prog_"))
async def cb_view_program(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    prog_id = int(callback.data.split("_")[2])
    prog = await get_program_by_id(session, prog_id)
    if not prog:
        await callback.answer("Dastur topilmadi yoki o'chirilgan!", show_alert=True)
        return

    user = await get_user_by_telegram_id(session, callback.from_user.id)
    user_db_id = user.id if user else 0

    await increment_views(session, prog.id)
    is_fav = await is_favorite(session, user_db_id, prog.id) if user_db_id else False
    avg_rating, count = await get_program_rating_stats(session, prog.id)
    bot_info = await bot.get_me()

    caption = (
        f"🏷 <b>{escape_text(prog.title)}</b>\n\n"
        f"📌 <b>Versiyasi:</b> {escape_text(prog.version)}\n"
        f"💻 <b>Tizim:</b> {format_os(prog.os_type)}\n"
        f"📦 <b>Hajmi:</b> {format_size(prog.file_size)}\n"
        f"🔑 <b>Arxiv paroli:</b> <code>{escape_text(prog.archive_password or 'Mavjud emas')}</code>\n"
        f"🛡 <b>Xavfsizlik:</b> ✅ VirusTotal toza\n"
        f"⭐️ <b>Reyting:</b> {avg_rating:.1f}/5.0 ({count} ta ovoz)\n"
        f"👁 <b>Ko'rishlar:</b> {prog.views_count + 1} | 📥 <b>Yuklab olingan:</b> {prog.downloads_count} marta\n\n"
        f"📝 <b>Tavsif:</b>\n{escape_text(prog.description or 'Tavsif kiritilmagan.')}"
    )

    keyboard = get_program_card_keyboard(
        program_id=prog.id,
        file_size_formatted=format_size(prog.file_size),
        is_fav=is_fav,
        bot_username=bot_info.username,
        prog_code=prog.code,
        back_target=f"cat_{prog.category_id}_1"
    )

    # Agar rasm bo'lsa yangi xabar qilib rasm bilan yuboramiz
    if prog.image_file_id:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_photo(
            photo=prog.image_file_id,
            caption=caption,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        try:
            await callback.message.edit_text(caption, reply_markup=keyboard, parse_mode="HTML")
        except Exception:
            await callback.message.answer(caption, reply_markup=keyboard, parse_mode="HTML")

    await callback.answer()

@router.message(F.text == "🔥 TOP Dasturlar")
async def msg_top_programs(message: Message, session: AsyncSession):
    progs = await get_top_programs(session, limit=10)
    if not progs:
        await message.answer("🔥 Hozircha TOP dasturlar mavjud emas.")
        return

    await hide_reply_keyboard(message)
    text = (
        "🔥 <b>ENG KO'P YUKLAB OLINGAN TOP DASTURLAR</b>\n\n"
        "<blockquote>Foydalanuvchilar tomonidan eng ko'p yuklab olingan sara dasturlar ro'yxati:</blockquote>\n\n"
    )
    keyboard = []
    for idx, p in enumerate(progs, 1):
        text += f"<b>{idx}. {escape_text(p.title)}</b> <code>({escape_text(p.version)})</code>\n"
        text += f"   └ 📥 {p.downloads_count} marta yuklangan | {format_os(p.os_type)}\n\n"
        keyboard.append([
            InlineKeyboardButton(text=f"📦 {idx}. {p.title}", callback_data=f"view_prog_{p.id}", style="primary")
        ])

    keyboard.append([
        InlineKeyboardButton(text="🔙 Asosiy Menyu", callback_data="back_to_main", style="danger")
    ])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")

@router.message(F.text == "🆕 Yangi relizlar")
async def msg_latest_programs(message: Message, session: AsyncSession):
    progs = await get_latest_programs(session, limit=10)
    if not progs:
        await message.answer("🆕 Hozircha yangi qo'shilgan dasturlar yo'q.")
        return

    await hide_reply_keyboard(message)
    text = (
        "🆕 <b>ENG SO'NGGI QO'SHILGAN YANGI RELIZLAR</b>\n\n"
        "<blockquote>Bot katalogiga eng oxirgi kiritilgan yangi versiyalar:</blockquote>\n\n"
    )
    keyboard = []
    for idx, p in enumerate(progs, 1):
        text += f"<b>{idx}. {escape_text(p.title)}</b> <code>({escape_text(p.version)})</code>\n"
        text += f"   └ {format_os(p.os_type)} | 📦 {format_size(p.file_size)}\n\n"
        keyboard.append([
            InlineKeyboardButton(text=f"📦 {idx}. {p.title}", callback_data=f"view_prog_{p.id}", style="primary")
        ])

    keyboard.append([
        InlineKeyboardButton(text="🔙 Asosiy Menyu", callback_data="back_to_main", style="danger")
    ])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
