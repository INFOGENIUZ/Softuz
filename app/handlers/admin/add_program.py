from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.repositories import (
    get_all_categories, get_category_by_id, create_program
)
from app.keyboards.inline_admin import (
    get_os_selection_keyboard, get_admin_categories_select_keyboard,
    get_skip_or_cancel_keyboard, get_confirm_program_upload_keyboard
)
from app.utils.formatters import format_size, format_os, escape_text

router = Router(name="add_program_router")

class AddProgramState(StatesGroup):
    waiting_file = State()
    waiting_title = State()
    waiting_version = State()
    waiting_os = State()
    waiting_category = State()
    waiting_password = State()
    waiting_description = State()
    waiting_image = State()
    waiting_confirm = State()

@router.callback_query(F.data == "admin_add_prog")
async def cb_start_add_program(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("Ruxsat berilmagan!", show_alert=True)
        return

    await state.clear()
    await state.set_state(AddProgramState.waiting_file)

    text = (
        "➕ <b>Yangi dastur yuklash (1-bosqich):</b>\n\n"
        "Iltimos, dasturning faylini yuboring (masalan: <code>.exe</code>, <code>.apk</code>, <code>.zip</code>, <code>.rar</code>, <code>.dmg</code> va h.k. 2 GB gacha):\n\n"
        "<i>Bekor qilish uchun pastdagi tugmani bosing.</i>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_cancel", style="danger")]]
    )
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_cancel")
async def cb_admin_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer("❌ Jarayon bekor qilindi.")
    await callback.answer()

# 1-QADAM: FAYL QABUL QILISH
@router.message(AddProgramState.waiting_file, F.document)
async def process_file(message: Message, state: FSMContext, bot: Bot):
    doc = message.document
    file_id = doc.file_id
    file_unique_id = doc.file_unique_id
    file_name = doc.file_name or "program_archive.zip"
    file_size = doc.file_size or 0

    storage_msg_id = None
    # Yopiq arxiv kanaliga nusxalash (Cloud storage)
    if settings.STORAGE_CHANNEL_ID:
        try:
            forwarded = await bot.send_document(
                chat_id=settings.STORAGE_CHANNEL_ID,
                document=file_id,
                caption=f"📦 Dastur: {escape_text(file_name)} | Hajmi: {format_size(file_size)}"
            )
            storage_msg_id = forwarded.message_id
        except Exception:
            storage_msg_id = None

    await state.update_data(
        file_id=file_id,
        file_unique_id=file_unique_id,
        file_name=file_name,
        file_size=file_size,
        storage_msg_id=storage_msg_id
    )

    await state.set_state(AddProgramState.waiting_title)
    text = (
        f"✅ Fayl qabul qilindi: <b>{escape_text(file_name)}</b> ({format_size(file_size)})\n\n"
        f"📝 <b>2-bosqich: Dastur nomini kiriting:</b>\n"
        f"(Masalan: <code>Adobe Photoshop 2024</code> yoki <code>Telegram Desktop</code>)"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_cancel", style="danger")]]
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

# 2-QADAM: DASTUR NOMI
@router.message(AddProgramState.waiting_title, F.text)
async def process_title(message: Message, state: FSMContext):
    title = message.text.strip()
    await state.update_data(title=title)

    await state.set_state(AddProgramState.waiting_version)
    text = (
        f"🏷 Dastur nomi: <b>{escape_text(title)}</b>\n\n"
        f"📌 <b>3-bosqich: Dastur versiyasini kiriting:</b>\n"
        f"(Masalan: <code>v25.2.0 RePack</code> yoki <code>v4.16.8</code>)"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_cancel", style="danger")]]
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

# 3-QADAM: VERSIYA
@router.message(AddProgramState.waiting_version, F.text)
async def process_version(message: Message, state: FSMContext):
    version = message.text.strip()
    await state.update_data(version=version)

    await state.set_state(AddProgramState.waiting_os)
    text = "💻 <b>4-bosqich: Dastur qaysi operatsion tizim uchun mo'ljallangan?</b>"
    await message.answer(text, reply_markup=get_os_selection_keyboard(), parse_mode="HTML")

# 4-QADAM: OS TANLASH (Callback)
@router.callback_query(AddProgramState.waiting_os, F.data.startswith("os_"))
async def process_os(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    os_code = callback.data.split("_")[1]
    await state.update_data(os_type=os_code)

    categories = await get_all_categories(session, active_only=True)
    if not categories:
        await callback.answer("Kategoriyalar mavjud emas, avval kategoriya qo'shing!", show_alert=True)
        return

    await state.set_state(AddProgramState.waiting_category)
    text = "📂 <b>5-bosqich: Dastur qaysi bo'lim (kategoriya)ga tegishli?</b>"
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_categories_select_keyboard(categories), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_admin_categories_select_keyboard(categories), parse_mode="HTML")
    await callback.answer()

# 5-QADAM: KATEGORIYA TANLASH (Callback)
@router.callback_query(AddProgramState.waiting_category, F.data.startswith("selcat_"))
async def process_category(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    cat_id = int(callback.data.split("_")[1])
    cat = await get_category_by_id(session, cat_id)
    cat_name = cat.name if cat else "Noma'lum"
    await state.update_data(category_id=cat_id, category_name=cat_name)

    await state.set_state(AddProgramState.waiting_password)
    text = (
        f"📂 Kategoriya: <b>{escape_text(cat_name)}</b>\n\n"
        f"🔑 <b>6-bosqich: Arxiv paroli bormi?</b>\n"
        f"Agar parol bo'lsa yozib yuboring (masalan: <code>dasturlar_bot</code>).\n"
        f"Agar parolsiz bo'lsa, «⏭ O'tkazib yuborish» tugmasini bosing:"
    )
    keyboard = get_skip_or_cancel_keyboard(skip_cb="skip_password")
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# 6-QADAM: PAROL (Yoki o'tkazib yuborish)
@router.callback_query(AddProgramState.waiting_password, F.data == "skip_password")
async def process_skip_password(callback: CallbackQuery, state: FSMContext):
    await state.update_data(archive_password=None)
    await state.set_state(AddProgramState.waiting_description)
    text = (
        "📝 <b>7-bosqich: Dastur haqida qisqacha tavsif va o'rnatish yo'riqnomasini yozing:</b>\n"
        "(Dasturning asosiy imkoniyatlari, tizim talablari va o'rnatish bo'yicha maslahatlar)"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_cancel", style="danger")]]
    )
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.message(AddProgramState.waiting_password, F.text)
async def process_password(message: Message, state: FSMContext):
    pwd = message.text.strip()
    await state.update_data(archive_password=pwd)

    await state.set_state(AddProgramState.waiting_description)
    text = (
        f"🔑 Arxiv paroli: <code>{escape_text(pwd)}</code>\n\n"
        f"📝 <b>7-bosqich: Dastur haqida qisqacha tavsif va o'rnatish yo'riqnomasini yozing:</b>\n"
        f"(Dasturning asosiy imkoniyatlari, tizim talablari va o'rnatish bo'yicha maslahatlar)"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_cancel", style="danger")]]
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

# 7-QADAM: TAVSIF
@router.message(AddProgramState.waiting_description, F.text)
async def process_description(message: Message, state: FSMContext):
    desc = message.text.strip()
    await state.update_data(description=desc)

    await state.set_state(AddProgramState.waiting_image)
    text = (
        "🖼 <b>8-bosqich: Dastur logosi yoki skrinshoti rasmini yuboring:</b>\n\n"
        "<i>Agar rasm qo'ymoqchi bo'lmasangiz, «⏭ O'tkazib yuborish» tugmasini bosing:</i>"
    )
    keyboard = get_skip_or_cancel_keyboard(skip_cb="skip_image")
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

# 8-QADAM: RASM (Yoki o'tkazib yuborish)
@router.callback_query(AddProgramState.waiting_image, F.data == "skip_image")
async def process_skip_image(callback: CallbackQuery, state: FSMContext):
    await state.update_data(image_file_id=None)
    await show_confirmation(callback.message, state)
    await callback.answer()

@router.message(AddProgramState.waiting_image, F.photo)
async def process_image(message: Message, state: FSMContext):
    photo = message.photo[-1]
    await state.update_data(image_file_id=photo.file_id)
    await show_confirmation(message, state)

async def show_confirmation(target_message: Message, state: FSMContext):
    data = await state.get_data()
    await state.set_state(AddProgramState.waiting_confirm)

    pwd_str = f"<code>{escape_text(data.get('archive_password'))}</code>" if data.get('archive_password') else "Parolsiz"
    preview = (
        "🔍 <b>YANGI DASTUR MA'LUMOTLARINI TEKSHIRING:</b>\n\n"
        f"🏷 <b>Nomi:</b> {escape_text(data.get('title'))}\n"
        f"📌 <b>Versiyasi:</b> {escape_text(data.get('version'))}\n"
        f"💻 <b>Tizim:</b> {format_os(data.get('os_type'))}\n"
        f"📂 <b>Kategoriya:</b> {escape_text(data.get('category_name'))}\n"
        f"📦 <b>Fayl:</b> {escape_text(data.get('file_name'))} ({format_size(data.get('file_size'))})\n"
        f"🔑 <b>Parol:</b> {pwd_str}\n\n"
        f"📝 <b>Tavsif:</b>\n{escape_text(data.get('description'))}\n\n"
        "<i>Ma'lumotlar to'g'ri bo'lsa, «✅ Tasdiqlash va chop etish» tugmasini bosing:</i>"
    )

    image_id = data.get("image_file_id")
    keyboard = get_confirm_program_upload_keyboard()

    if image_id:
        try:
            await target_message.answer_photo(
                photo=image_id,
                caption=preview,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            return
        except Exception:
            pass

    await target_message.answer(preview, reply_markup=keyboard, parse_mode="HTML")

# 9-QADAM: TASDIQLASH VA CHOP ETISH
@router.callback_query(AddProgramState.waiting_confirm, F.data == "confirm_upload")
async def process_confirm_upload(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    await state.clear()

    prog = await create_program(
        session=session,
        title=data["title"],
        category_id=data["category_id"],
        os_type=data["os_type"],
        version=data["version"],
        description=data["description"],
        file_id=data["file_id"],
        file_name=data["file_name"],
        file_size=data["file_size"],
        archive_password=data.get("archive_password"),
        file_unique_id=data.get("file_unique_id"),
        storage_msg_id=data.get("storage_msg_id"),
        image_file_id=data.get("image_file_id")
    )

    bot_info = await bot.get_me()
    deep_link = f"https://t.me/{bot_info.username}?start={prog.code}"

    success_text = (
        f"🎉 <b>Dastur muvaffaqiyatli saqlandi va chop etildi!</b>\n\n"
        f"📦 <b>Nomi:</b> {escape_text(prog.title)} ({escape_text(prog.version)})\n"
        f"🆔 <b>Kod:</b> <code>{prog.code}</code>\n"
        f"🔗 <b>To'g'ridan-to'g'ri havola:</b> <code>{deep_link}</code>\n\n"
        f"<i>Ushbu havolani kanalingizga yoki guruhlarga joylab, o'quvchilarni to'g'ridan-to'g'ri dasturga yo'naltirishingiz mumkin!</i>"
    )
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(success_text, parse_mode="HTML")
    await callback.answer("Dastur saqlandi!", show_alert=True)
