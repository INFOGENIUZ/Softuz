from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.database.models import Program
from app.database.repositories import get_program_by_id, delete_program
from app.keyboards.inline_admin import get_manage_program_keyboard
from app.utils.paginator import Paginator
from app.utils.formatters import format_size, format_os, escape_text

router = Router(name="manage_programs_router")

@router.callback_query(F.data.startswith("admin_prog_list_"))
async def cb_admin_program_list(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("Ruxsat berilmagan!", show_alert=True)
        return

    page = int(callback.data.split("_")[3])
    per_page = 6
    offset = (page - 1) * per_page

    total_count = (await session.execute(select(func.count(Program.id)))).scalar() or 0
    if total_count == 0:
        await callback.answer("Hozircha bazada dasturlar yo'q.", show_alert=True)
        return

    stmt = select(Program).order_by(Program.id.desc()).limit(per_page).offset(offset)
    programs = list((await session.execute(stmt)).scalars().all())

    paginator = Paginator(total_items=total_count, page=page, per_page=per_page)
    keyboard = []
    for p in programs:
        keyboard.append([
            InlineKeyboardButton(text=f"📦 {p.title} ({p.version})", callback_data=f"admin_view_prog_{p.id}", style="primary")
        ])

    nav_row = []
    if paginator.has_prev:
        nav_row.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"admin_prog_list_{paginator.prev_page}", style="primary"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {paginator.page}/{paginator.total_pages}", callback_data="noop"))
    if paginator.has_next:
        nav_row.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"admin_prog_list_{paginator.next_page}", style="primary"))
    keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton(text="🔙 Admin Menyusi", callback_data="admin_menu", style="danger")])

    text = f"📋 <b>Barcha dasturlar ro'yxati</b> (Jami: {total_count} ta):\n<i>Tahrirlash yoki o'chirish uchun dasturni tanlang:</i>"
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("admin_view_prog_"))
async def cb_admin_view_prog(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("Ruxsat berilmagan!", show_alert=True)
        return

    prog_id = int(callback.data.split("_")[3])
    prog = await get_program_by_id(session, prog_id)
    if not prog:
        await callback.answer("Dastur topilmadi!", show_alert=True)
        return

    text = (
        f"📦 <b>Dastur boshqaruvi:</b>\n\n"
        f"🏷 <b>Nomi:</b> {escape_text(prog.title)}\n"
        f"📌 <b>Versiyasi:</b> {escape_text(prog.version)}\n"
        f"💻 <b>OS:</b> {format_os(prog.os_type)}\n"
        f"📦 <b>Hajmi:</b> {format_size(prog.file_size)}\n"
        f"🔑 <b>Parol:</b> <code>{escape_text(prog.archive_password or 'Yoq')}</code>\n"
        f"📥 <b>Yuklab olingan:</b> {prog.downloads_count} marta\n"
        f"👁 <b>Ko'rilgan:</b> {prog.views_count} marta\n"
        f"🆔 <b>Kod:</b> <code>{prog.code}</code>"
    )
    keyboard = get_manage_program_keyboard(prog.id)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("admin_del_prog_"))
async def cb_admin_del_prog(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("Ruxsat berilmagan!", show_alert=True)
        return

    prog_id = int(callback.data.split("_")[3])
    deleted = await delete_program(session, prog_id)
    if deleted:
        await callback.answer("🗑 Dastur muvaffaqiyatli o'chirildi!", show_alert=True)
    else:
        await callback.answer("Dastur topilmadi!", show_alert=True)

    # Ro'yxatga qaytish
    cb_data = callback
    cb_data.data = "admin_prog_list_1"
    await cb_admin_program_list(cb_data, session)
