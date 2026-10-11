from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.repositories import get_active_channels, add_mandatory_channel, delete_mandatory_channel
from app.utils.formatters import escape_text

router = Router(name="admin_channels_router")

class AddChannelState(StatesGroup):
    waiting_channel_id = State()
    waiting_title = State()
    waiting_url = State()

@router.callback_query(F.data == "admin_channels")
async def cb_admin_channels(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    if callback.from_user.id not in settings.admin_ids:
        return

    channels = await get_active_channels(session)
    text = (
        "📢 <b>Majburiy obuna (Homiy kanallar):</b>\n\n"
        "Foydalanuvchilar botdan foydalanishi uchun quyidagi kanallarga a'zo bo'lishi shart bo'ladi.\n"
        "<i>Eslatma: Bot ushbu kanallarda administrator bo'lishi kerak!</i>\n\n"
    )

    keyboard = [
        [InlineKeyboardButton(text="➕ Yangi kanal qo'shish", callback_data="add_new_channel")]
    ]

    for ch in channels:
        keyboard.append([
            InlineKeyboardButton(text=f"📢 {ch.channel_title}", url=ch.channel_url),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"delchan_{ch.channel_id}")
        ])

    keyboard.append([InlineKeyboardButton(text="🔙 Admin Menyusi", callback_data="admin_menu")])

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")

@router.callback_query(F.data == "add_new_channel")
async def cb_add_channel_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AddChannelState.waiting_channel_id)
    text = (
        "➕ <b>1-qadam: Kanal ID raqamini kiriting:</b>\n\n"
        "Kanal ID raqami odatda <code>-100</code> bilan boshlanadi (masalan: <code>-1001234567890</code>).\n"
        "<i>(Kanal ID sini @userinfobot yoki boshqa info botlar orqali olishingiz mumkin):</i>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_channels")]]
    )
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.message(AddChannelState.waiting_channel_id, F.text)
async def process_channel_id(message: Message, state: FSMContext):
    raw_id = message.text.strip()
    if not (raw_id.isdigit() or (raw_id.startswith("-") and raw_id[1:].isdigit())):
        await message.answer("⚠️ Iltimos, faqat raqamlardan iborat ID kiriting (masalan: -1001234567890):")
        return

    await state.update_data(channel_id=int(raw_id))
    await state.set_state(AddChannelState.waiting_title)
    await message.answer("🏷 <b>2-qadam: Kanal nomini kiriting:</b>\n(Masalan: <i>Rasmiy Dasturlar Kanali</i>):", parse_mode="HTML")

@router.message(AddChannelState.waiting_title, F.text)
async def process_channel_title(message: Message, state: FSMContext):
    title = message.text.strip()
    await state.update_data(channel_title=title)
    await state.set_state(AddChannelState.waiting_url)
    await message.answer("🔗 <b>3-qadam: Kanal taklif havolasini kiriting:</b>\n(Masalan: <i>https://t.me/kanal_nomi</i>):", parse_mode="HTML")

@router.message(AddChannelState.waiting_url, F.text)
async def process_channel_url(message: Message, state: FSMContext, session: AsyncSession):
    url = message.text.strip()
    if not (url.startswith("https://t.me/") or url.startswith("http://t.me/")):
        await message.answer("⚠️ Havola https://t.me/ bilan boshlanishi kerak:")
        return

    data = await state.get_data()
    await state.clear()

    await add_mandatory_channel(
        session=session,
        channel_id=data["channel_id"],
        channel_title=data["channel_title"],
        channel_url=url
    )

    await message.answer(
        f"✅ <b>Kanal muvaffaqiyatli qo'shildi!</b>\n\n"
        f"📢 Nomi: {escape_text(data['channel_title'])}\n"
        f"🆔 ID: <code>{data['channel_id']}</code>\n"
        f"🔗 Havola: {escape_text(url)}",
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("delchan_"))
async def cb_delete_channel(callback: CallbackQuery, session: AsyncSession):
    channel_id = int(callback.data.split("_")[1])
    await delete_mandatory_channel(session, channel_id)
    await callback.answer("🗑 Kanal o'chirildi!", show_alert=True)
    await cb_admin_channels(callback, session)
