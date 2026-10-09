from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, Message

def get_main_reply_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Foydalanuvchi va admin uchun asosiy doimiy menyu tugmalari."""
    keyboard = [
        [
            KeyboardButton(text="🔍 Dastur qidirish")
        ],
        [
            KeyboardButton(text="📂 Kategoriyalar"),
            KeyboardButton(text="🔥 TOP Dasturlar")
        ],
        [
            KeyboardButton(text="🆕 Yangi relizlar"),
            KeyboardButton(text="⭐ Saqlanganlar")
        ],
        [
            KeyboardButton(text="💡 Dastur so'rash"),
            KeyboardButton(text="ℹ️ Bot haqida / Yordam")
        ]
    ]

    if is_admin:
        keyboard.append([KeyboardButton(text="🛠 Admin panel")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Kerakli bo'limni tanlang yoki qidiruv nomini yozing..."
    )

def get_cancel_reply_keyboard() -> ReplyKeyboardMarkup:
    """Jarayonni bekor qilish tugmasi."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

async def hide_reply_keyboard(message: Message) -> None:
    """Inline tugmalar ochilganda Reply klaviaturani ekrandan tozalash/yopish."""
    try:
        tmp = await message.answer("⏳", reply_markup=ReplyKeyboardRemove())
        await tmp.delete()
    except Exception:
        pass

