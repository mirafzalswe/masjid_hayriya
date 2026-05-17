import html
import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from .states import MurojaatState, SearchState, YordamState
from .keyboards import (
    main_menu_kb, muhtojlik_kb, priority_kb, tasdiqlash_kb,
    shaxs_pick_kb, yordam_turi_kb, yordam_tasdiq_kb,
)
from .db import (
    is_hodim,
    get_hodim_info,
    murojaat_saqlash,
    qabul_qilgan_murojaatlar,
    barcha_murojaatlar,
    shaxs_qidirish,
    shaxs_qisqa_info,
    yordam_saqlash,
)

router = Router()
log = logging.getLogger(__name__)

TUR_NOMI = {
    'oziq_ovqat': '🍞 Oziq-ovqat',
    'dori':       '💊 Dori-darmon',
    'ijara':      '🏠 Ijara/uy-joy',
    'toy':        "💒 To'y yordami",
    'taziya':     "🕌 Ta'ziya",
    'talim':      "📚 Ta'lim/maktab",
    'kasalxona':  '🏥 Davolash',
    'boshqa':     '📋 Boshqa',
}

PR_NOMI = {
    '1': '🔴 Yuqori',
    '2': "🟡 O'rta",
    '3': '🟢 Past',
}

YORDAM_TURI_NOMI = {
    'pul':        '💵 Pul',
    'oziq_ovqat': '🍞 Oziq-ovqat',
    'kiyim':      '👕 Kiyim-kechak',
    'dori':       '💊 Dori-darmon',
    'mahsulot':   '📦 Mahsulot/jihoz',
    'xizmat':     '🛠 Xizmat',
    'boshqa':     '📋 Boshqa',
}


# ────────────────────────────────────────────────────────
# Kirish tekshiruvi — faqat ro'yxatdagi hodimlar
# ────────────────────────────────────────────────────────

async def check_access(message: Message) -> bool:
    """Foydalanuvchi hodimlar ro'yxatida bor-yo'qligini tekshiradi"""
    if not await is_hodim(message.from_user.id):
        await message.answer(
            "🔒 *Kirish taqiqlangan*\n\n"
            "Bu bot faqat masjid hodimlariga mo'ljallangan.\n\n"
            "Kirishga ruxsat olish uchun masjid administratori bilan bog'laning.\n"
            "Administrator sizning Telegram ID ingizni tizimga qo'shishi kerak:\n"
            f"`{message.from_user.id}`",
            parse_mode="Markdown",
        )
        return False
    return True


# ────────────────────────────────────────────────────────
# /start
# ────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    if not await is_hodim(message.from_user.id):
        await message.answer(
            "🔒 *Kirish taqiqlangan*\n\n"
            "Bu bot faqat masjid hodimlariga mo'ljallangan.\n\n"
            "Kirishga ruxsat olish uchun masjid administratoriga "
            "quyidagi ID ni yuboring:\n"
            f"`{message.from_user.id}`",
            parse_mode="Markdown",
        )
        return

    hodim = await get_hodim_info(message.from_user.id)
    ism = hodim['fio'] if hodim else message.from_user.first_name

    await message.answer(
        f"Assalomu Alaykum, *{ism}*! 🕌\n\n"
        f"Masjid Xayriya boshqaruv botiga xush kelibsiz.\n"
        f"Sizning rolingiz: *{hodim['role'] if hodim else 'Hodim'}*\n\n"
        "Yangi murojaat qabul qilish yoki ko'rish uchun "
        "quyidagi menyudan foydalaning 👇",
        parse_mode="Markdown",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("bekor"))
async def cmd_bekor(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Amal bekor qilindi.", reply_markup=main_menu_kb())


# ────────────────────────────────────────────────────────
# Bosh menyu
# ────────────────────────────────────────────────────────

@router.message(F.text == "📝 Yangi murojaat")
async def yangi_murojaat_start(message: Message, state: FSMContext):
    if not await check_access(message):
        return
    await state.clear()
    await message.answer(
        "📝 *Yangi murojaat qabul qilish*\n\n"
        "*1-qadam:* Murojaat qiluvchining to'liq ismini kiriting\n"
        "_Misol: Rahimov Bahodir Alijonovich_\n\n"
        "Bekor qilish: /bekor",
        parse_mode="Markdown",
    )
    await state.set_state(MurojaatState.fio)


@router.message(F.text == "👤 Mening murojaatlarim")
async def qabul_qilgan_handler(message: Message, state: FSMContext):
    if not await check_access(message):
        return
    await state.clear()

    murojaatlar = await qabul_qilgan_murojaatlar(message.from_user.id)
    if not murojaatlar:
        await message.answer(
            "📭 Siz hali bot orqali birorta murojaat kiritmagansiz.\n\n"
            "Yangi murojaat kiritish uchun *📝 Yangi murojaat* tugmasini bosing.",
            parse_mode="Markdown",
            reply_markup=main_menu_kb(),
        )
        return

    matn = "👤 *Siz kiritgan so'nggi murojaatlar:*\n\n"
    for m in murojaatlar:
        matn += (
            f"{m['holat_emoji']} *#{m['pk']}* — {m['shaxs']}\n"
            f"   🏷 {m['tur']} · 📅 {m['sana']}\n"
            f"   Holat: {m['holat_nomi']}\n\n"
        )
    await message.answer(matn, parse_mode="Markdown", reply_markup=main_menu_kb())


@router.message(F.text == "📋 Barcha murojaatlar")
async def barcha_murojaatlar_handler(message: Message, state: FSMContext):
    if not await check_access(message):
        return
    await state.clear()

    murojaatlar = await barcha_murojaatlar(limit=10)
    if not murojaatlar:
        await message.answer(
            "📭 Hali birorta murojaat kiritilmagan.",
            reply_markup=main_menu_kb(),
        )
        return

    matn = "📋 *So'nggi murojaatlar (barcha hodimlar):*\n\n"
    for m in murojaatlar:
        matn += (
            f"{m['holat_emoji']} *#{m['pk']}* — {m['shaxs']}\n"
            f"   🏷 {m['tur']} · 📅 {m['sana']}\n"
            f"   📞 `{m['telefon']}`\n"
            f"   Holat: {m['holat_nomi']} · Qo'shgan: {m['kim_qoshgan']}\n\n"
        )
    await message.answer(matn, parse_mode="Markdown", reply_markup=main_menu_kb())


@router.message(F.text == "🔍 Qidiruv")
async def qidiruv_start(message: Message, state: FSMContext):
    if not await check_access(message):
        return
    await state.clear()
    await message.answer(
        "🔍 *Shaxs qidirish*\n\n"
        "Quyidagilardan birini yuboring:\n"
        "• 👤 F.I.O (yoki uning bir qismi)\n"
        "• 📞 Telefon raqami\n"
        "• 🏠 Manzil\n\n"
        "Eng kamida 2 ta belgi.\n"
        "Bekor qilish: /bekor",
        parse_mode="Markdown",
    )
    await state.set_state(SearchState.query)


@router.message(SearchState.query)
async def qidiruv_natija(message: Message, state: FSMContext):
    query = (message.text or '').strip()
    if len(query) < 2:
        await message.answer(
            "❌ So'rov juda qisqa. Kamida 2 ta belgi kiriting.\n"
            "Bekor qilish: /bekor"
        )
        return

    natija = await shaxs_qidirish(query, limit=10)
    await state.clear()

    if not natija:
        await message.answer(
            f"🤷 <b>{html.escape(query)}</b> bo'yicha hech narsa topilmadi.\n\n"
            "Boshqa so'rov kiriting yoki menyudan foydalaning 👇",
            parse_mode="HTML",
            reply_markup=main_menu_kb(),
        )
        return

    qatorlar = [
        f"🔎 <b>«{html.escape(query)}»</b> bo'yicha topildi: <b>{len(natija)}</b>\n"
    ]
    for s in natija:
        qator = (
            f"👤 <b>{html.escape(s['fio'])}</b>\n"
            f"   📞 <code>{html.escape(s['telefon'])}</code>"
        )
        if s['manzil']:
            qator += f"\n   🏠 {html.escape(s['manzil'])}"
        qator += f"\n   📋 Murojaatlar: <b>{s['murojaat_soni']}</b>"
        if s['oxirgi_sana']:
            qator += f" · oxirgisi: {s['oxirgi_sana']}"
        qatorlar.append(qator)

    matn = "\n\n".join(qatorlar)
    if len(natija) == 10:
        matn += "\n\n<i>Faqat dastlabki 10 ta natija ko'rsatildi.</i>"

    await message.answer(matn, parse_mode="HTML", reply_markup=main_menu_kb())


# ────────────────────────────────────────────────────────
# Yordam qo'shish — wizard
# ────────────────────────────────────────────────────────

@router.message(F.text == "💝 Yordam qo'shish")
async def yordam_start(message: Message, state: FSMContext):
    if not await check_access(message):
        return
    await state.clear()
    await message.answer(
        "💝 *Yordam qo'shish*\n\n"
        "*1-qadam:* Yordam beriluvchi shaxsni qidiring.\n"
        "Ism, telefon yoki manzilni yuboring (kamida 2 belgi).\n\n"
        "Bekor qilish: /bekor",
        parse_mode="Markdown",
    )
    await state.set_state(YordamState.qidiruv)


@router.message(YordamState.qidiruv)
async def yordam_qidiruv(message: Message, state: FSMContext):
    query = (message.text or '').strip()
    if len(query) < 2:
        await message.answer("❌ Kamida 2 belgi kiriting. Bekor qilish: /bekor")
        return

    natija = await shaxs_qidirish(query, limit=5)
    if not natija:
        await message.answer(
            f"🤷 «{query}» bo'yicha hech kim topilmadi.\n\n"
            "Boshqa so'rov yuboring yoki avval /start orqali shaxsni murojaat sifatida qo'shing.\n"
            "Bekor qilish: /bekor"
        )
        return

    await message.answer(
        f"🔎 Topildi: *{len(natija)}* ta. Quyidagilardan birini tanlang:",
        parse_mode="Markdown",
        reply_markup=shaxs_pick_kb(natija),
    )
    await state.set_state(YordamState.shaxs_tanlash)


@router.callback_query(F.data == "ycancel")
async def yordam_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Yordam qo'shish bekor qilindi.")
    await callback.message.answer("Bosh menyu:", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(YordamState.shaxs_tanlash, F.data.startswith("yshaxs:"))
async def yordam_shaxs_picked(callback: CallbackQuery, state: FSMContext):
    shaxs_pk = int(callback.data.split(":")[1])
    await state.update_data(shaxs_pk=shaxs_pk)
    await callback.message.edit_text("✅ Shaxs tanlandi.")
    await callback.message.answer(
        "*2-qadam:* Yordam turini tanlang 👇",
        parse_mode="Markdown",
        reply_markup=yordam_turi_kb(),
    )
    await state.set_state(YordamState.turi)
    await callback.answer()


@router.callback_query(YordamState.turi, F.data.startswith("yturi:"))
async def yordam_turi_picked(callback: CallbackQuery, state: FSMContext):
    turi = callback.data.split(":")[1]
    turi_nomi = YORDAM_TURI_NOMI.get(turi, turi)
    await state.update_data(turi=turi, turi_nomi=turi_nomi)
    await callback.message.edit_text(f"✅ Yordam turi: *{turi_nomi}*", parse_mode="Markdown")

    if turi == 'pul':
        await callback.message.answer(
            "*3-qadam:* Miqdorni so'mda kiriting.\n"
            "_Masalan: 200000_",
            parse_mode="Markdown",
        )
        await state.set_state(YordamState.miqdor)
    else:
        await callback.message.answer(
            "*3-qadam:* Yordam tafsilotini yozing.\n"
            "_Masalan: «5 kg sahar, 2L moy, 3 kg go'sht»_",
            parse_mode="Markdown",
        )
        await state.set_state(YordamState.mazmun)
    await callback.answer()


@router.message(YordamState.miqdor)
async def yordam_miqdor(message: Message, state: FSMContext):
    raw = (message.text or '').strip().replace(' ', '').replace("'", '').replace('`', '')
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(
            "❌ Faqat raqam yuboring (so'mda).\n_Masalan: 200000_\n"
            "Bekor qilish: /bekor",
            parse_mode="Markdown",
        )
        return
    await state.update_data(miqdor=int(raw), mazmun='')
    await _yordam_ask_bergan_fio(message, state)


@router.message(YordamState.mazmun)
async def yordam_mazmun(message: Message, state: FSMContext):
    mazmun = (message.text or '').strip()
    if len(mazmun) < 3:
        await message.answer("❌ Tafsilot juda qisqa (kamida 3 belgi). Bekor qilish: /bekor")
        return
    await state.update_data(mazmun=mazmun, miqdor=None)
    await _yordam_ask_bergan_fio(message, state)


async def _yordam_ask_bergan_fio(message: Message, state: FSMContext):
    await message.answer(
        "*4-qadam:* Yordamni kim berdi? (Familiya Ism)\n"
        "_Noma'lum bo'lsa: /skip_",
        parse_mode="Markdown",
    )
    await state.set_state(YordamState.bergan_fio)


@router.message(YordamState.bergan_fio, Command("skip"))
async def yordam_bergan_fio_skip(message: Message, state: FSMContext):
    await state.update_data(bergan_fio="Noma'lum")
    await _yordam_ask_bergan_telefon(message, state)


@router.message(YordamState.bergan_fio)
async def yordam_bergan_fio(message: Message, state: FSMContext):
    fio = (message.text or '').strip()
    if len(fio) < 3:
        await message.answer(
            "❌ Ism juda qisqa (kamida 3 belgi). Yoki /skip — noma'lum.\n"
            "Bekor qilish: /bekor"
        )
        return
    await state.update_data(bergan_fio=fio)
    await _yordam_ask_bergan_telefon(message, state)


async def _yordam_ask_bergan_telefon(message: Message, state: FSMContext):
    await message.answer(
        "*5-qadam:* Telefon raqami (ixtiyoriy)\n"
        "_Masalan: +998 90 123 45 67. O'tkazib yuborish: /skip_",
        parse_mode="Markdown",
    )
    await state.set_state(YordamState.bergan_telefon)


@router.message(YordamState.bergan_telefon, Command("skip"))
async def yordam_bergan_telefon_skip(message: Message, state: FSMContext):
    await state.update_data(bergan_telefon='')
    await _yordam_show_confirm(message, state)


@router.message(YordamState.bergan_telefon)
async def yordam_bergan_telefon(message: Message, state: FSMContext):
    raw = (message.text or '').strip()
    digits = raw.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if not digits.isdigit() or len(digits) < 9:
        await message.answer(
            "❌ Telefon noto'g'ri formatda.\n"
            "_Masalan: +998 90 123 45 67_. O'tkazib yuborish: /skip\n"
            "Bekor qilish: /bekor",
            parse_mode="Markdown",
        )
        return
    await state.update_data(bergan_telefon=raw)
    await _yordam_show_confirm(message, state)


async def _yordam_show_confirm(message: Message, state: FSMContext):
    d = await state.get_data()
    info = await shaxs_qisqa_info(d['shaxs_pk'])
    shaxs_str = f"{info['fio']} ({info['telefon']})" if info else f"#{d['shaxs_pk']}"
    miqdor_str = f"{d['miqdor']:,} so'm".replace(',', ' ') if d.get('miqdor') else '—'
    mazmun_str = d.get('mazmun') or '—'
    telefon_str = d.get('bergan_telefon') or '—'

    await message.answer(
        "📋 *Yordam ma'lumotlari:*\n\n"
        f"👤 *Olgan:* {shaxs_str}\n"
        f"🏷 *Turi:* {d['turi_nomi']}\n"
        f"💰 *Miqdor:* {miqdor_str}\n"
        f"📝 *Tavsif:* {mazmun_str}\n"
        f"🤝 *Kim berdi:* {d['bergan_fio']}\n"
        f"📞 *Telefon:* {telefon_str}\n\n"
        "━━━━━━━━━━━━━━━\n"
        "Saqlasinmi?",
        parse_mode="Markdown",
        reply_markup=yordam_tasdiq_kb(),
    )
    await state.set_state(YordamState.tasdiqlash)


@router.callback_query(YordamState.tasdiqlash, F.data.startswith("ytasdiq:"))
async def yordam_tasdiqlash(callback: CallbackQuery, state: FSMContext):
    javob = callback.data.split(":")[1]

    if javob == "yoq":
        await state.clear()
        await callback.message.edit_text("❌ Yordam bekor qilindi.")
        await callback.message.answer("Bosh menyu:", reply_markup=main_menu_kb())
        await callback.answer()
        return

    d = await state.get_data()
    try:
        res = await yordam_saqlash(
            shaxs_pk=d['shaxs_pk'],
            turi=d['turi'],
            miqdor=d.get('miqdor'),
            mazmun=d.get('mazmun') or '',
            bergan_fio=d['bergan_fio'],
            bergan_telefon=d.get('bergan_telefon') or '',
            telegram_id=callback.from_user.id,
        )
        await callback.message.edit_text(
            f"✅ *Yordam #{res['pk']} saqlandi!*\n\n"
            f"👤 Olgan: {res['shaxs']}\n"
            f"🏷 {d['turi_nomi']}",
            parse_mode="Markdown",
        )
        await callback.message.answer("Bosh menyu:", reply_markup=main_menu_kb())
        log.info(f"Yangi yordam #{res['pk']} → {res['shaxs']} (hodim: {callback.from_user.id})")
    except Exception as e:
        log.error(f"Yordam saqlashda xato: {e}")
        await callback.message.edit_text("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        await callback.message.answer("Bosh menyu:", reply_markup=main_menu_kb())

    await state.clear()
    await callback.answer()


# ────────────────────────────────────────────────────────


@router.message(F.text == "ℹ️ Ma'lumot")
async def malumot_handler(message: Message, state: FSMContext):
    if not await check_access(message):
        return
    await state.clear()
    await message.answer(
        "🕌 *Masjid Xayriya — Boshqaruv Boti*\n\n"
        "Bu bot masjid hodimlariga nochor kishilarning murojaatlarini "
        "tezda qabul qilib, bazaga saqlash imkonini beradi.\n\n"
        "📌 *Bot orqali kiritilgan ma'lumotlar:*\n"
        "• Murojaat qiluvchining F.I.O\n"
        "• Telefon raqami\n"
        "• Muhtojlik turi\n"
        "• Murojaat mazmuni\n"
        "• Muhimlik darajasi\n\n"
        "📌 *Muhtojlik turlari:*\n"
        "🍞 Oziq-ovqat · 💊 Dori-darmon\n"
        "📚 Ta'lim · 🏥 Davolash · 📋 Boshqa\n\n"
        "📌 *Muhimlik darajalari:*\n"
        "🔴 Yuqori — tezkor yordam\n"
        "🟡 O'rta — yaqin orada\n"
        "🟢 Past — kechiktirilishi mumkin\n\n"
        "💻 Barcha murojaatlarni web interfeys orqali ko'rish mumkin.",
        parse_mode="Markdown",
        reply_markup=main_menu_kb(),
    )


# ────────────────────────────────────────────────────────
# FSM bosqichlari
# ────────────────────────────────────────────────────────

@router.message(MurojaatState.fio)
async def step_fio(message: Message, state: FSMContext):
    fio = message.text.strip()
    if len(fio) < 5:
        await message.answer(
            "❌ To'liq ism-familiya kiriting (kamida 5 ta harf).\n"
            "_Misol: Rahimov Bahodir Alijonovich_",
            parse_mode="Markdown",
        )
        return
    await state.update_data(fio=fio)
    await message.answer(
        f"✅ *{fio}*\n\n"
        "*2-qadam:* Telefon raqamini kiriting:\n"
        "_Misol: +998901234567_",
        parse_mode="Markdown",
    )
    await state.set_state(MurojaatState.telefon)


@router.message(MurojaatState.telefon)
async def step_telefon(message: Message, state: FSMContext):
    telefon = message.text.strip()
    tozalangan = telefon.replace('+', '').replace(' ', '').replace('-', '')
    if not tozalangan.isdigit() or len(tozalangan) < 9:
        await message.answer(
            "❌ Noto'g'ri format.\n_Misol: +998901234567_",
            parse_mode="Markdown",
        )
        return
    await state.update_data(telefon=telefon)
    await message.answer(
        "✅ Qabul qilindi!\n\n*3-qadam:* Muhtojlik turini tanlang 👇",
        parse_mode="Markdown",
        reply_markup=muhtojlik_kb(),
    )
    await state.set_state(MurojaatState.muhtojlik_turi)


@router.callback_query(MurojaatState.muhtojlik_turi, F.data.startswith("tur:"))
async def step_muhtojlik_turi(callback: CallbackQuery, state: FSMContext):
    tur_kod = callback.data.split(":")[1]
    tur_nomi = TUR_NOMI.get(tur_kod, tur_kod)
    await state.update_data(muhtojlik_turi=tur_kod, muhtojlik_turi_nomi=tur_nomi)
    await callback.message.edit_text(f"✅ Tanlandi: *{tur_nomi}*", parse_mode="Markdown")
    await callback.message.answer(
        "*4-qadam:* Murojaat mazmunini batafsil yozing:\n\n"
        "_Muhtojlikning sababi, ahvol, oila holati va "
        "boshqa muhim ma'lumotlarni kiriting._",
        parse_mode="Markdown",
    )
    await state.set_state(MurojaatState.mazmun)
    await callback.answer()


@router.message(MurojaatState.mazmun)
async def step_mazmun(message: Message, state: FSMContext):
    mazmun = message.text.strip()
    if len(mazmun) < 10:
        await message.answer("❌ Batafsilroq yozing (kamida 10 ta belgi).")
        return
    await state.update_data(mazmun=mazmun)
    await message.answer(
        "✅ Qabul qilindi!\n\n*5-qadam:* Muhimlik darajasini tanlang 👇",
        parse_mode="Markdown",
        reply_markup=priority_kb(),
    )
    await state.set_state(MurojaatState.priority)


@router.callback_query(MurojaatState.priority, F.data.startswith("pr:"))
async def step_priority(callback: CallbackQuery, state: FSMContext):
    pr_val = int(callback.data.split(":")[1])
    pr_nomi = PR_NOMI.get(str(pr_val), str(pr_val))
    await state.update_data(priority=pr_val, priority_nomi=pr_nomi)
    await callback.message.edit_text(f"✅ Muhimlik: *{pr_nomi}*", parse_mode="Markdown")

    d = await state.get_data()
    await callback.message.answer(
        "📋 *Murojaat ma'lumotlari:*\n\n"
        f"👤 *F.I.O:* {d['fio']}\n"
        f"📞 *Telefon:* {d['telefon']}\n"
        f"🏷 *Muhtojlik:* {d['muhtojlik_turi_nomi']}\n"
        f"⚡ *Muhimlik:* {d['priority_nomi']}\n\n"
        f"📝 *Mazmun:*\n_{d['mazmun']}_\n\n"
        "━━━━━━━━━━━━━━━\n"
        "Murojaatni bazaga saqlasinmi?",
        parse_mode="Markdown",
        reply_markup=tasdiqlash_kb(),
    )
    await state.set_state(MurojaatState.tasdiqlash)
    await callback.answer()


@router.callback_query(MurojaatState.tasdiqlash, F.data.startswith("tasdiq:"))
async def step_tasdiqlash(callback: CallbackQuery, state: FSMContext):
    javob = callback.data.split(":")[1]

    if javob == "yoq":
        await state.clear()
        await callback.message.edit_text("❌ Murojaat bekor qilindi.")
        await callback.message.answer("Bosh menyu:", reply_markup=main_menu_kb())
        await callback.answer()
        return

    d = await state.get_data()
    tg_user = callback.from_user

    try:
        murojaat_id = await murojaat_saqlash(
            fio=d['fio'],
            telefon=d['telefon'],
            muhtojlik_turi=d['muhtojlik_turi'],
            mazmun=d['mazmun'],
            priority=d['priority'],
            telegram_id=tg_user.id,
            telegram_username=tg_user.username or '',
        )
        await callback.message.edit_text(
            f"✅ *Murojaat #{murojaat_id} bazaga saqlandi!*\n\n"
            f"👤 {d['fio']}\n"
            f"🏷 {d['muhtojlik_turi_nomi']} · ⚡ {d['priority_nomi']}\n\n"
            f"Web interfeys orqali ko'rish va boshqarish mumkin.",
            parse_mode="Markdown",
        )
        await callback.message.answer("Keyingi murojaat uchun tayyor:", reply_markup=main_menu_kb())
        log.info(f"Yangi murojaat #{murojaat_id} — {d['fio']} (hodim: {tg_user.id})")

    except Exception as e:
        log.error(f"Murojaat saqlashda xato: {e}")
        await callback.message.edit_text(
            "❌ Xatolik yuz berdi. Qaytadan urinib ko'ring."
        )
        await callback.message.answer("Bosh menyu:", reply_markup=main_menu_kb())

    await state.clear()
    await callback.answer()


@router.message()
async def unknown_handler(message: Message, state: FSMContext):
    if not await is_hodim(message.from_user.id):
        await message.answer(
            "🔒 Kirish taqiqlangan.\n"
            f"Telegram ID ingiz: `{message.from_user.id}`",
            parse_mode="Markdown",
        )
        return
    cur = await state.get_state()
    if cur:
        await message.answer("⚠️ Ko'rsatmaga amal qiling. Bekor qilish: /bekor")
    else:
        await message.answer("Menyudan foydalaning 👇", reply_markup=main_menu_kb())
