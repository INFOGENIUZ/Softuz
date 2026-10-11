from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.repositories import (
    get_or_create_user, get_program_by_code, get_program_by_id,
    increment_views, is_favorite, get_program_rating_stats,
    get_active_channels
)
from app.keyboards.reply import get_main_reply_keyboard, hide_reply_keyboard
from app.keyboards.inline_user import get_program_card_keyboard, get_about_keyboard
from app.utils.formatters import format_size, format_os, escape_text

router = Router(name="common_router")

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, session: AsyncSession, bot: Bot, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    is_admin = user_id in settings.admin_ids

    # Foydalanuvchini bazaga qo'shish / yangilash
    user = await get_or_create_user(
        session=session,
        telegram_id=user_id,
        full_name=message.from_user.full_name,
        username=message.from_user.username,
        is_admin=is_admin
    )

    # Deep-link parametrini tekshirish (masalan: /start prog_12 yoki /start 12)
    args = command.args
    if args:
        code = args.strip()
        if not code.startswith("prog_") and code.isdigit():
            code = f"prog_{code}"

        prog = await get_program_by_code(session, code)
        if prog:
            await increment_views(session, prog.id)
            is_fav = await is_favorite(session, user.id, prog.id)
            avg_rating, count = await get_program_rating_stats(session, prog.id)
            from app.utils.cache import cache
            bot_username = cache.get_bot_username()
            if not bot_username:
                try:
                    bot_info = await bot.get_me()
                    bot_username = bot_info.username
                    cache.set_bot_username(bot_username)
                except Exception:
                    bot_username = "dasturlar_bot"

            caption = (
                f"🏷 <b>{escape_text(prog.title)}</b>\n\n"
                f"📌 <b>Versiyasi:</b> {escape_text(prog.version)}\n"
                f"💻 <b>Tizim:</b> {format_os(prog.os_type)}\n"
                f"📦 <b>Hajmi:</b> {format_size(prog.file_size)}\n"
                f"🔑 <b>Arxiv paroli:</b> <code>{escape_text(prog.archive_password or 'Mavjud emas')}</code>\n"
                f"🛡 <b>Xavfsizlik:</b> ✅ VirusTotal tekshirilgan\n"
                f"⭐️ <b>Reyting:</b> {avg_rating:.1f}/5.0 ({count} ta ovoz)\n"
                f"📥 <b>Yuklab olingan:</b> {prog.downloads_count} marta\n\n"
                f"📝 <b>Tavsif:</b>\n{escape_text(prog.description or 'Tavsif kiritilmagan.')}"
            )

            keyboard = get_program_card_keyboard(
                program_id=prog.id,
                file_size_formatted=format_size(prog.file_size),
                is_fav=is_fav,
                bot_username=bot_username,
                prog_code=prog.code,
                back_target="open_categories",
                download_url=prog.download_url
            )

            if prog.image_file_id:
                try:
                    await message.answer_photo(
                        photo=prog.image_file_id,
                        caption=caption,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                    return
                except Exception:
                    pass

            await message.answer(caption, reply_markup=keyboard, parse_mode="HTML")
            return

    # Standart /start tabriknomasi
    welcome_text = (
        f"👋 <b>Assalomu alaykum, {escape_text(message.from_user.first_name)}!</b>\n\n"
        f"🚀 <b>Dasturlar botiga xush kelibsiz!</b>\n"
        f"Ushbu bot orqali siz kompyuter (Windows, macOS) va telefon (Android) uchun eng kerakli va sara dasturlarni, "
        f"arxivlarni to'g'ridan-to'g'ri Telegramdan tezkor yuklab olishingiz mumkin.\n\n"
        f"👇 Kerakli bo'limni tanlang yoki qidiruvdan foydalaning:"
    )

    await message.answer(
        welcome_text,
        reply_markup=get_main_reply_keyboard(is_admin=is_admin),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "check_subscription")
async def cb_check_subscription(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    user_id = callback.from_user.id
    channels = await get_active_channels(session)
    unsubscribed = []

    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch.channel_id, user_id=user_id)
            if member.status in ["left", "kicked"]:
                unsubscribed.append(ch.channel_title)
        except Exception:
            continue

    if unsubscribed:
        await callback.answer(
            f"❌ Siz hali hamma kanallarga a'zo bo'lmadingiz!\nQolgan kanallar: {', '.join(unsubscribed)}",
            show_alert=True
        )
    else:
        await callback.answer("✅ Rahmat! Barcha kanallarga muvaffaqiyatli a'zo bo'ldingiz.", show_alert=True)
        is_admin = user_id in settings.admin_ids
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            "🎉 <b>A'zolik tasdiqlandi!</b>\nEndi botdan to'liq foydalanishingiz mumkin:",
            reply_markup=get_main_reply_keyboard(is_admin=is_admin),
            parse_mode="HTML"
        )

@router.message(F.text == "ℹ️ Bot haqida / Yordam")
@router.message(F.text.in_(["/help", "/about"]))
async def msg_help(message: Message):
    await hide_reply_keyboard(message)
    help_text = (
        "ℹ️ <b>DASTURLAR PLATFORMASI — RASMIY QO'LLANMA VA YORDAM</b>\n\n"
        "<blockquote>⚡️ <i>Kompyuter va mobil qurilmalar uchun eng sara, xavfsiz hamda so'nggi versiyadagi dasturlar markazi.</i></blockquote>\n\n"
        "🔹 <b>1. Dasturni qanday topish va yuklab olish mumkin?</b>\n"
        "• <b>Qidiruv:</b> «<code>🔍 Dastur qidirish</code>» orqali nomini yozing (masalan: <i>Photoshop</i>, <i>WinRAR</i>, <i>CapCut</i>).\n"
        "• <b>Katalog:</b> «<code>📂 Kategoriyalar</code>» bo'limida dasturlar yo'nalishlar bo'yicha to'liq tartiblangan.\n"
        "• <b>Yuklab olish:</b> Dastur kartochkasidagi «<code>⬇️ Yuklab olish</code>» tugmasini bosing — fayl to'g'ridan-to'g'ri Telegram orqali yuqori tezlikda yuboriladi.\n\n"
        "🔹 <b>2. Arxiv paroli va xavfsizlik kafolati:</b>\n"
        "• Har bir fayl bazaga yuklanishdan oldin <b>VirusTotal</b> tekshiruvidan o'tkaziladi.\n"
        "• Agar arxivda parol bo'lsa, u dastur ma'lumotlaridagi <code>Arxiv paroli</code> qatorida aniq ko'rsatiladi.\n\n"
        "🔹 <b>3. Arxivdan chiqarish dasturlari:</b>\n"
        "• <b>Kompyuter (Windows/macOS):</b> <i>WinRAR</i> yoki <i>7-Zip</i> dasturlari orqali.\n"
        "• <b>Mobil telefon (Android/iOS):</b> <i>ZArchiver</i> yoki <i>RAR</i> ilovasi orqali.\n\n"
        "🔹 <b>4. Kerakli dastur topilmadimi?</b>\n"
        "• «<code>💡 Dastur so'rash</code>» bo'limiga kirib buyurtma qoldiring — adminlar uni tez orada botga yuklashadi!\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👨‍💻 <b>Dasturchi va texnik qo'llab-quvvatlash:</b>\n"
        "Savol, taklif yoki texnik murojaatlar bo'yicha rasmiy aloqa:\n"
        "👉 <a href=\"https://t.me/developer_muxa\">@developer_muxa</a>"
    )
    await message.answer(
        help_text,
        reply_markup=get_about_keyboard(),
        parse_mode="HTML",
        disable_web_page_preview=True
    )

@router.callback_query(F.data == "back_to_main")
async def cb_back_to_main(callback: CallbackQuery):
    await callback.answer()
    is_admin = callback.from_user.id in settings.admin_ids
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        "👇 <b>Asosiy menyu:</b>\n<i>Kerakli bo'limni tanlang yoki qidiruv nomini yozing:</i>",
        reply_markup=get_main_reply_keyboard(is_admin=is_admin),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()

