import os
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.repositories import (
    get_full_statistics, get_pending_requests, update_request_status
)
from app.utils.formatters import escape_text, format_os

router = Router(name="stats_backup_router")

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("Ruxsat berilmagan!", show_alert=True)
        return

    stats = await get_full_statistics(session)

    top_text = ""
    for idx, p in enumerate(stats["top_programs"], 1):
        top_text += f"{idx}. {escape_text(p.title)} — {p.downloads_count} marta\n"
    if not top_text:
        top_text = "Mavjud emas\n"

    text = (
        "📊 <b>BOTNING TO'LIQ STATISTIKASI:</b>\n\n"
        "👥 <b>Foydalanuvchilar:</b>\n"
        f"• Jami obunachilar: <b>{stats['total_users']} ta</b>\n"
        f"• Faollar: <b>{stats['active_users']} ta</b>\n"
        f"• Botni bloklaganlar: <b>{stats['blocked_users']} ta</b>\n"
        f"• Bugun qo'shilganlar: <b>+{stats['today_users']} ta</b>\n\n"
        "📦 <b>Dasturlar bazasi:</b>\n"
        f"• Jami dasturlar soni: <b>{stats['total_programs']} ta</b>\n"
        f"• Windows: {stats['win_count']} | Android: {stats['apk_count']} | Mac: {stats['mac_count']}\n"
        f"• Jami yuklab olishlar: <b>{stats['total_downloads']} marta</b>\n\n"
        "📩 <b>Kutilayotgan buyurtmalar:</b>\n"
        f"• Ko'rib chiqilishi kerak: <b>{stats['pending_reqs']} ta</b>\n\n"
        "🔥 <b>TOP-3 Eng ommabop dasturlar:</b>\n"
        f"{top_text}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Admin Menyusi", callback_data="admin_menu", style="danger")]]
    )

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_backup")
async def cb_admin_backup(callback: CallbackQuery):
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("Ruxsat berilmagan!", show_alert=True)
        return

    db_path = "data/bot_database.sqlite3"
    if not os.path.exists(db_path):
        await callback.answer("Baza fayli topilmadi!", show_alert=True)
        return

    await callback.answer("⏳ Baza fayli tayyorlanmoqda...", show_alert=False)

    now_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
    backup_file = FSInputFile(
        path=db_path,
        filename=f"backup_dasturlar_bot_{now_str}.sqlite3"
    )

    caption = (
        f"💾 <b>Ma'lumotlar bazasi zaxira nusxasi (Backup)</b>\n\n"
        f"📅 Sana: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"🛡 Ushbu faylni xavfsiz joyda saqlang!"
    )

    await callback.message.answer_document(
        document=backup_file,
        caption=caption,
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_requests")
async def cb_admin_requests(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("Ruxsat berilmagan!", show_alert=True)
        return

    requests = await get_pending_requests(session, limit=10)
    if not requests:
        await callback.answer("Hozircha yangi dastur buyurtmalari yo'q.", show_alert=True)
        return

    text = "📩 <b>Kutilayotgan so'nggi dastur buyurtmalari:</b>\n\n"
    keyboard = []

    for req in requests:
        uname = f"@{req.username}" if req.username else f"ID: {req.telegram_id}"
        text += f"• <b>#{req.id}:</b> {escape_text(req.app_name)} ({uname})\n"
        keyboard.append([
            InlineKeyboardButton(text=f"✅ #{req.id} Bajarildi", callback_data=f"req_done_{req.id}", style="success"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"req_reject_{req.id}", style="danger")
        ])

    keyboard.append([InlineKeyboardButton(text="🔙 Admin Menyusi", callback_data="admin_menu", style="danger")])

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("req_done_"))
async def cb_request_done(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    req_id = int(callback.data.split("_")[2])
    req = await update_request_status(session, req_id, "approved")
    if req:
        # Foydalanuvchiga xushxabar jo'natish
        try:
            user_msg = (
                f"🎉 <b>Xushxabar!</b>\n\n"
                f"Siz buyurtma qilgan <b>«{escape_text(req.app_name)}»</b> dasturi botga yuklandi!\n"
                f"Uni «🔍 Dastur qidirish» orqali topib yuklab olishingiz mumkin."
            )
            await bot.send_message(chat_id=req.telegram_id, text=user_msg, parse_mode="HTML")
        except Exception:
            pass

    await callback.answer("✅ Buyurtma bajarildi deb belgilandi!", show_alert=True)
    await cb_admin_requests(callback, session)

@router.callback_query(F.data.startswith("req_reject_"))
async def cb_request_reject(callback: CallbackQuery, session: AsyncSession):
    req_id = int(callback.data.split("_")[2])
    await update_request_status(session, req_id, "rejected")
    await callback.answer("❌ Buyurtma rad etildi.", show_alert=True)
    await cb_admin_requests(callback, session)
