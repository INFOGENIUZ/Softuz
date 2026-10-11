from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.database.models import Category, Program, MandatoryChannel
from app.utils.paginator import Paginator

def get_categories_keyboard(categories: List[Category]) -> InlineKeyboardMarkup:
    """Kategoriyalar ro'yxati inline klaviaturasi (2 tadan qator qilib)."""
    keyboard = []
    row = []
    for cat in categories:
        row.append(
            InlineKeyboardButton(
                text=f"{cat.icon} {cat.name}",
                callback_data=f"cat_{cat.id}_1",
                style="primary"
            )
        )
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Qo'shimcha bosh menyuga qaytish
    keyboard.append([
        InlineKeyboardButton(text="🔙 Asosiy Menyu", callback_data="back_to_main", style="danger")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_programs_list_keyboard(
    programs: List[Program],
    paginator: Paginator,
    prefix: str = "cat",
    extra_id: int = 0
) -> InlineKeyboardMarkup:
    """Dasturlar ro'yxati va sahifalash (Pagination) klaviaturasi."""
    keyboard = []

    # Dasturlar ro'yxati
    for prog in programs:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📦 {prog.title} ({prog.version})",
                callback_data=f"view_prog_{prog.id}",
                style="primary"
            )
        ])

    # Sahifalash (Paginator) qatori
    nav_row = []
    if paginator.has_prev:
        nav_row.append(
            InlineKeyboardButton(
                text="◀️ Oldingi",
                callback_data=f"page_{prefix}_{extra_id}_{paginator.prev_page}",
                style="primary"
            )
        )

    nav_row.append(
        InlineKeyboardButton(
            text=f"📄 {paginator.page}/{paginator.total_pages}",
            callback_data="noop"
        )
    )

    if paginator.has_next:
        nav_row.append(
            InlineKeyboardButton(
                text="Keyingi ▶️",
                callback_data=f"page_{prefix}_{extra_id}_{paginator.next_page}",
                style="primary"
            )
        )

    if len(nav_row) > 1:
        keyboard.append(nav_row)

    # Qidirish va Orqaga
    keyboard.append([
        InlineKeyboardButton(text="🔍 Qidirish", callback_data="prompt_search", style="success"),
        InlineKeyboardButton(text="🔙 Bo'limlarga qaytish", callback_data="open_categories", style="danger")
    ])
    keyboard.append([
        InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="back_to_main", style="danger")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_program_card_keyboard(
    program_id: int,
    file_size_formatted: str,
    is_fav: bool,
    bot_username: str,
    prog_code: str,
    back_target: str = "open_categories",
    download_url: Optional[str] = None
) -> InlineKeyboardMarkup:
    """Dastur kartochkasi ostidagi to'liq boshqaruv tugmalari."""
    fav_icon = "❤️ Saqlangan" if is_fav else "⭐ Saqlash"
    share_url = f"https://t.me/share/url?url=https://t.me/{bot_username}?start={prog_code}&text=Ushbu dasturni yuklab oling!"

    keyboard = [
        [
            InlineKeyboardButton(
                text=f"⬇️ Telegramdan yuklash ({file_size_formatted})",
                callback_data=f"dl_{program_id}"
            )
        ]
    ]

    # Agar tezkor bulutli havola mavjud bo'lsa
    if download_url:
        keyboard.append([
            InlineKeyboardButton(
                text="🌐 Tezkor Bulutdan yuklash (Direct Link)",
                url=download_url
            )
        ])

    keyboard.extend([
        [
            InlineKeyboardButton(text=fav_icon, callback_data=f"fav_{program_id}"),
            InlineKeyboardButton(text="⭐️ Baholash (1-5)", callback_data=f"rate_{program_id}")
        ],
        [
            InlineKeyboardButton(text="📢 Do'stlarga ulashish", url=share_url)
        ],
        [
            InlineKeyboardButton(text="⚠️ Ishlamayaptimi?", callback_data=f"report_{program_id}"),
            InlineKeyboardButton(text="🔙 Orqaga", callback_data=back_target)
        ],
        [
            InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="back_to_main")
        ]
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_rating_keyboard(program_id: int) -> InlineKeyboardMarkup:
    """Dasturni 1 dan 5 gacha baholash inline tugmalari."""
    keyboard = [
        [
            InlineKeyboardButton(text="1 ⭐", callback_data=f"setrate_{program_id}_1", style="primary"),
            InlineKeyboardButton(text="2 ⭐", callback_data=f"setrate_{program_id}_2", style="primary"),
            InlineKeyboardButton(text="3 ⭐", callback_data=f"setrate_{program_id}_3", style="primary"),
            InlineKeyboardButton(text="4 ⭐", callback_data=f"setrate_{program_id}_4", style="primary"),
            InlineKeyboardButton(text="5 ⭐", callback_data=f"setrate_{program_id}_5", style="primary"),
        ],
        [
            InlineKeyboardButton(text="🔙 Bekor qilish", callback_data=f"view_prog_{program_id}", style="danger")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_subscription_keyboard(channels: List[MandatoryChannel]) -> InlineKeyboardMarkup:
    """Majburiy a'zo bo'linishi kerak bo'lgan kanallar va tekshirish tugmasi."""
    keyboard = []
    for idx, ch in enumerate(channels, 1):
        keyboard.append([
            InlineKeyboardButton(
                text=f"{idx}. {ch.channel_title}",
                url=ch.channel_url
            )
        ])
    keyboard.append([
        InlineKeyboardButton(
            text="🔄 A'zolikni tekshirish",
            callback_data="check_subscription",
            style="success"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_search_empty_keyboard() -> InlineKeyboardMarkup:
    """Qidiruv bo'yicha hech narsa topilmaganda chiquvchi tugmalar."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💡 Ushbu dasturni buyurtma qilish", callback_data="start_request_app", style="success")
            ],
            [
                InlineKeyboardButton(text="📂 Kategoriyalarni ko'rish", callback_data="open_categories", style="primary")
            ],
            [
                InlineKeyboardButton(text="🔙 Asosiy Menyu", callback_data="back_to_main", style="danger")
            ]
        ]
    )

def get_about_keyboard() -> InlineKeyboardMarkup:
    """Bot haqida va qo'llab-quvvatlash uchun inline tugmalar."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👨‍💻 Qo'llab-quvvatlash / Dasturchi",
                    url="https://t.me/developer_muxa"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Asosiy Menyu",
                    callback_data="back_to_main",
                    style="danger"
                )
            ]
        ]
    )

