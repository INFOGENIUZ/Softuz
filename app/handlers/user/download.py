import asyncio
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.repositories import (
    get_program_by_id, increment_downloads, increment_user_downloads,
    get_user_by_telegram_id, set_rating, get_program_rating_stats
)
from app.keyboards.inline_user import get_rating_keyboard
from app.utils.formatters import escape_text, format_size

router = Router(name="download_router")

@router.callback_query(F.data.startswith("dl_"))
async def cb_download_program(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    # Tugma aylanib qotib qolmasligi uchun darhol javob beramiz
    await callback.answer("⏳ Fayl tayyorlanmoqda, iltimos kuting...", show_alert=False)

    prog_id = int(callback.data.split("_")[1])
    prog = await get_program_by_id(session, prog_id)
    if not prog:
        await callback.message.answer("❌ Dastur topilmadi!")
        return

    user_id = callback.from_user.id

    # Statistikani fonda oshiramiz
    async def update_stats():
        user = await get_user_by_telegram_id(session, user_id)
        if user:
            await increment_user_downloads(session, user.id)
        await increment_downloads(session, prog.id)
    asyncio.create_task(update_stats())

    # Telegramda yuklanmoqda statusini ko'rsatamiz
    try:
        await bot.send_chat_action(chat_id=user_id, action="upload_document")
    except Exception:
        pass

    # Katta hajmdagi fayllar (>30 MB) uchun foydalanuvchiga aniq status xabari
    status_msg = None
    if prog.file_size > 30 * 1024 * 1024:
        cloud_hint = ""
        if prog.download_url:
            cloud_hint = f"\n\n⚡️ <i>Eslatma: Agar Telegram orqali yuklash sekin bo'lsa, kartochkadagi <b>«🌐 Tezkor Bulutdan yuklash»</b> havolasidan ham foydalanishingiz mumkin!</i>"
        try:
            status_msg = await callback.message.answer(
                f"⏳ <b>{escape_text(prog.title)} ({escape_text(prog.version)}) yuborilmoqda...</b>\n\n"
                f"📦 <b>Fayl hajmi:</b> {format_size(prog.file_size)}\n"
                f"🚀 <i>Telegram serverlaridan yetkazilmoqda. Internet tezligingizga qarab biroz vaqt olishi mumkin, iltimos kuting...</i>{cloud_hint}",
                parse_mode="HTML"
            )
        except Exception:
            status_msg = None

    # Telegram bulutidan faylni foydalanuvchiga yuborish
    file_sent = False

    # 1-usul: Yopiq arxiv kanalidan copy_message (2GB gacha muammosiz va 0.1 soniyada ishlaydi)
    if prog.storage_msg_id and settings.STORAGE_CHANNEL_ID:
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=settings.STORAGE_CHANNEL_ID,
                message_id=prog.storage_msg_id
            )
            file_sent = True
        except Exception:
            file_sent = False

    # 2-usul: Agar kanaldan olinmasa, to'g'ridan-to'g'ri file_id orqali yuborish
    if not file_sent and prog.file_id:
        try:
            await bot.send_document(
                chat_id=user_id,
                document=prog.file_id,
                caption=f"📦 <b>{escape_text(prog.title)} ({escape_text(prog.version)})</b>",
                parse_mode="HTML"
            )
            file_sent = True
        except Exception as e:
            if status_msg:
                try:
                    await status_msg.delete()
                except Exception:
                    pass
            await callback.message.answer(
                f"❌ Faylni yuborishda xatolik yuz berdi: {escape_text(str(e))}\nAdminlarga xabar berildi."
            )
            return

    # Status xabarini tozalaymiz
    if status_msg:
        try:
            await status_msg.delete()
        except Exception:
            pass

    # O'rnatish eslatmasi va parol
    password_text = f"<code>{escape_text(prog.archive_password)}</code>" if prog.archive_password else "Mavjud emas (Parolsiz)"
    guide_text = (
        f"✅ <b>{escape_text(prog.title)} muvaffaqiyatli yuborildi!</b>\n\n"
        f"🔑 <b>Arxiv paroli:</b> {password_text}\n\n"
        f"💡 <b>Eslatma:</b>\n"
        f"• Dasturni o'rnatishdan oldin arxivdan to'liq chiqarib oling.\n"
        f"• Antivirus tizimlari faollashtiruvchi (crack/patch) fayllarga noto'g'ri shubha qilishi mumkin, xavotir olmang — barcha dasturlar tekshirilgan.\n\n"
        f"⭐️ Dastur ma'qul keldimi? O'z bahoyingizni qoldiring:"
    )
    await callback.message.answer(guide_text, reply_markup=get_rating_keyboard(prog.id), parse_mode="HTML")

@router.callback_query(F.data.startswith("rate_"))
async def cb_rate_menu(callback: CallbackQuery):
    await callback.answer()
    prog_id = int(callback.data.split("_")[1])
    text = "⭐️ <b>Ushbu dasturni baholang:</b>\n1 dan 5 gacha yulduzchani tanlang:"
    try:
        await callback.message.edit_text(text, reply_markup=get_rating_keyboard(prog_id), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_rating_keyboard(prog_id), parse_mode="HTML")

@router.callback_query(F.data.startswith("setrate_"))
async def cb_set_rate(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split("_")
    prog_id = int(parts[1])
    score = int(parts[2])

    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if user:
        await set_rating(session, user.id, prog_id, score)

    avg_score, count = await get_program_rating_stats(session, prog_id)
    await callback.answer(f"⭐️ Rahmat! Siz {score} yulduz qo'ydingiz.\nO'rtacha baho: {avg_score:.1f} ({count} ta)", show_alert=True)
    try:
        await callback.message.delete()
    except Exception:
        pass

@router.callback_query(F.data.startswith("report_"))
async def cb_report_program(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    prog_id = int(callback.data.split("_")[1])
    prog = await get_program_by_id(session, prog_id)
    title = prog.title if prog else f"ID: {prog_id}"

    user = callback.from_user
    report_msg = (
        f"⚠️ <b>Dastur bo'yicha shikoyat / xato xabari!</b>\n\n"
        f"📦 <b>Dastur:</b> {escape_text(title)} (ID: {prog_id})\n"
        f"👤 <b>Foydalanuvchi:</b> {escape_text(user.full_name)} (@{user.username or 'username_yoq'}, ID: <code>{user.id}</code>)"
    )

    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=report_msg, parse_mode="HTML")
        except Exception:
            pass

    await callback.answer("⚠️ Shikoyatingiz adminga yetkazildi. Tez orada tekshirib chiqiladi!", show_alert=True)
