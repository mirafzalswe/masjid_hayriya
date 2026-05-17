from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Yangi murojaat"),
             KeyboardButton(text="💝 Yordam qo'shish")],
            [KeyboardButton(text="📋 Barcha murojaatlar"),
             KeyboardButton(text="👤 Mening murojaatlarim")],
            [KeyboardButton(text="🔍 Qidiruv"),
             KeyboardButton(text="ℹ️ Ma'lumot")],
        ],
        resize_keyboard=True,
        persistent=True,
    )


def muhtojlik_kb() -> InlineKeyboardMarkup:
    turlari = [
        ("🍞 Oziq-ovqat",    "oziq_ovqat"),
        ("💊 Dori-darmon",   "dori"),
        ("🏠 Ijara/uy-joy",  "ijara"),
        ("💒 To'y yordami",  "toy"),
        ("🕌 Ta'ziya",       "taziya"),
        ("📚 Ta'lim/maktab", "talim"),
        ("🏥 Davolash",      "kasalxona"),
        ("📋 Boshqa",        "boshqa"),
    ]
    # 2 ustunli qator
    buttons = []
    for i in range(0, len(turlari), 2):
        row = [InlineKeyboardButton(text=turlari[i][0], callback_data=f"tur:{turlari[i][1]}")]
        if i + 1 < len(turlari):
            row.append(InlineKeyboardButton(text=turlari[i+1][0], callback_data=f"tur:{turlari[i+1][1]}"))
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def priority_kb() -> InlineKeyboardMarkup:
    daraja = [
        ("🔴 Yuqori — Tezkor yordam kerak",       "1"),
        ("🟡 O'rta — Yaqin orada yordam kerak",    "2"),
        ("🟢 Past — Kechiktirilishi mumkin",        "3"),
    ]
    buttons = [[InlineKeyboardButton(text=d[0], callback_data=f"pr:{d[1]}")] for d in daraja]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def tasdiqlash_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Ha, yuborish", callback_data="tasdiq:ha"),
        InlineKeyboardButton(text="❌ Bekor qilish",  callback_data="tasdiq:yoq"),
    ]])


# ─── Yordam qo'shish ─────────────────────────────────────────────────────────

def shaxs_pick_kb(shaxs_list: list[dict]) -> InlineKeyboardMarkup:
    """Qidiruv natijasi — har bir shaxs uchun bitta tugma."""
    buttons = []
    for s in shaxs_list:
        label = f"👤 {s['fio']} · {s['telefon']}"
        # Telegram cheklovi: tugma matni 64 belgigacha
        if len(label) > 60:
            label = label[:57] + '…'
        buttons.append([
            InlineKeyboardButton(text=label, callback_data=f"yshaxs:{s['pk']}")
        ])
    buttons.append([
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="ycancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def yordam_turi_kb() -> InlineKeyboardMarkup:
    turlari = [
        ("💵 Pul",            "pul"),
        ("🍞 Oziq-ovqat",     "oziq_ovqat"),
        ("👕 Kiyim-kechak",   "kiyim"),
        ("💊 Dori-darmon",    "dori"),
        ("📦 Mahsulot/jihoz", "mahsulot"),
        ("🛠 Xizmat",         "xizmat"),
        ("📋 Boshqa",         "boshqa"),
    ]
    buttons = []
    for i in range(0, len(turlari), 2):
        row = [InlineKeyboardButton(text=turlari[i][0], callback_data=f"yturi:{turlari[i][1]}")]
        if i + 1 < len(turlari):
            row.append(InlineKeyboardButton(text=turlari[i+1][0], callback_data=f"yturi:{turlari[i+1][1]}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="ycancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def yordam_tasdiq_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Saqlash",       callback_data="ytasdiq:ha"),
        InlineKeyboardButton(text="❌ Bekor qilish",  callback_data="ytasdiq:yoq"),
    ]])
