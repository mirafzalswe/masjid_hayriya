"""
Django ORM ni async muhitda ishlatish uchun helper.
"""
import os
import sys
import django
from asgiref.sync import sync_to_async
from datetime import date


def setup_django():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'masjid_hayria.settings')
    django.setup()


@sync_to_async
def is_hodim(telegram_id: int) -> bool:
    """Telegram ID bo'yicha foydalanuvchi masjid hodimi ekanligini tekshiradi"""
    from murojaatlar.models import UserProfile
    return UserProfile.objects.filter(
        telegram_id=telegram_id,
        role__in=['admin', 'imam', 'hodim']
    ).exists()


@sync_to_async
def get_hodim_info(telegram_id: int) -> dict | None:
    """Hodim ma'lumotlarini qaytaradi"""
    from murojaatlar.models import UserProfile
    try:
        profile = UserProfile.objects.select_related('user').get(telegram_id=telegram_id)
        return {
            'fio': profile.user.get_full_name() or profile.user.username,
            'role': profile.get_role_display(),
        }
    except UserProfile.DoesNotExist:
        return None


@sync_to_async
def shaxs_qisqa_info(shaxs_pk: int) -> dict | None:
    """Bitta shaxs haqida qisqa ma'lumot (FIO + telefon)."""
    from murojaatlar.models import Shaxs
    try:
        s = Shaxs.objects.only('fio', 'telefon').get(pk=shaxs_pk)
    except Shaxs.DoesNotExist:
        return None
    return {'fio': s.fio, 'telefon': s.telefon}


@sync_to_async
def yordam_saqlash(
    shaxs_pk: int,
    turi: str,
    miqdor: int | None,
    mazmun: str,
    bergan_fio: str,
    bergan_telefon: str,
    telegram_id: int,
) -> dict:
    """Yangi yordam yozuvini saqlaydi.

    `telegram_id` orqali qabul qilgan hodimni topamiz (UserProfile.telegram_id).
    """
    from murojaatlar.models import Shaxs, Yordam, UserProfile
    from datetime import date as _date

    shaxs = Shaxs.objects.get(pk=shaxs_pk)
    hodim = None
    try:
        hodim = UserProfile.objects.select_related('user').get(telegram_id=telegram_id).user
    except UserProfile.DoesNotExist:
        pass

    yordam = Yordam.objects.create(
        shaxs=shaxs,
        turi=turi,
        miqdor=miqdor,
        mazmun=mazmun or '',
        bergan_fio=bergan_fio or "Noma'lum",
        bergan_telefon=bergan_telefon or '',
        sana=_date.today(),
        qabul_qilgan=hodim,
    )
    return {
        'pk':    yordam.pk,
        'shaxs': shaxs.fio,
    }


@sync_to_async
def murojaat_saqlash(
    fio: str,
    telefon: str,
    muhtojlik_turi: str,
    mazmun: str,
    priority: int,
    telegram_id: int,
    telegram_username: str = "",
) -> int:
    """Yangi murojaat va shaxsni bazaga saqlaydi. Murojaat ID sini qaytaradi."""
    from murojaatlar.models import Shaxs, Murojaat, normalize_phone

    # Normalize before lookup so we hit the same canonical row that the
    # web form would have stored.
    canonical = normalize_phone(telefon)
    shaxs, _ = Shaxs.objects.get_or_create(
        telefon=canonical,
        defaults={'fio': fio}
    )
    if shaxs.fio != fio:
        shaxs.fio = fio
        shaxs.save(update_fields=['fio'])

    murojaat = Murojaat.objects.create(
        shaxs=shaxs,
        muhtojlik_turi=muhtojlik_turi,
        mazmun=mazmun,
        priority=priority,
        holat='yangi',
        murojaat_sanasi=date.today(),
        telegram_id=telegram_id,
        telegram_username=telegram_username or '',
    )
    return murojaat.pk


@sync_to_async
def shaxs_qidirish(query: str, limit: int = 10) -> list:
    """Shaxslarni FIO, manzil yoki telefon bo'yicha qidiradi.

    Telefon qidiruvi normalize_phone bilan bir xil canonical formada bo'ladi,
    shuning uchun "+998 90 123" va "998901234567" bir xil natija beradi.
    """
    from django.db.models import Q, Count, Max
    from murojaatlar.models import Shaxs, normalize_phone

    q = (query or '').strip()
    if len(q) < 2:
        return []

    filters = Q(fio__icontains=q) | Q(manzil__icontains=q)
    digits = normalize_phone(q)
    if digits:
        filters |= Q(telefon__icontains=digits)

    qs = (
        Shaxs.objects
        .filter(filters)
        .annotate(
            murojaat_soni=Count('murojaatlar'),
            oxirgi_sana=Max('murojaatlar__murojaat_sanasi'),
        )
        .order_by('fio')[:limit]
    )

    natija = []
    for s in qs:
        natija.append({
            'pk': s.pk,
            'fio': s.fio,
            'telefon': s.telefon,
            'manzil': s.manzil or '',
            'murojaat_soni': s.murojaat_soni,
            'oxirgi_sana': s.oxirgi_sana.strftime('%d.%m.%Y') if s.oxirgi_sana else '',
        })
    return natija


_HOLAT_EMOJI = {
    'yangi': '🆕',
    'korib_chiqilmoqda': '👁',
    'yordam_berildi': '✅',
    'rad_etildi': '❌',
    'kechiktirildi': '⏳',
}
_HOLAT_NOMI = {
    'yangi': 'Yangi',
    'korib_chiqilmoqda': "Ko'rib chiqilmoqda",
    'yordam_berildi': 'Yordam berildi',
    'rad_etildi': 'Rad etildi',
    'kechiktirildi': 'Kechiktirildi',
}


def _murojaat_to_dict(m, *, include_kim_qoshgan: bool = False) -> dict:
    row = {
        'pk': m.pk,
        'shaxs': m.shaxs.fio,
        'telefon': m.shaxs.telefon,
        'tur': m.get_muhtojlik_turi_display(),
        'sana': m.murojaat_sanasi.strftime('%d.%m.%Y'),
        'holat_emoji': _HOLAT_EMOJI.get(m.holat, '❓'),
        'holat_nomi': _HOLAT_NOMI.get(m.holat, m.holat),
    }
    if include_kim_qoshgan:
        # `telegram_username` bot orqali kiritilganda to'ldiriladi.
        # Bot orqali emas (web) bo'lsa, kim qo'shganini bilmaymiz — '—' chiqaramiz.
        row['kim_qoshgan'] = f"@{m.telegram_username}" if m.telegram_username else "—"
    return row


@sync_to_async
def qabul_qilgan_murojaatlar(telegram_id: int) -> list:
    """Hodim qabul qilgan (kiritgan) so'ngi 5 ta murojaatni qaytaradi"""
    from murojaatlar.models import Murojaat
    qs = (
        Murojaat.objects
        .filter(telegram_id=telegram_id)
        .select_related('shaxs')
        .order_by('-yaratilgan')[:5]
    )
    return [_murojaat_to_dict(m) for m in qs]


@sync_to_async
def barcha_murojaatlar(limit: int = 10) -> list:
    """Barcha hodimlardan so'nggi N ta murojaat — umumiy ko'rinish."""
    from murojaatlar.models import Murojaat
    qs = (
        Murojaat.objects
        .select_related('shaxs')
        .order_by('-yaratilgan')[:limit]
    )
    return [_murojaat_to_dict(m, include_kim_qoshgan=True) for m in qs]
