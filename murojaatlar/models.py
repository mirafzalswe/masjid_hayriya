"""
Domain models — Masjid Xayriya.

Sources of truth for choices live here. Any consumer (web view, telegram bot,
admin, exports) must import from this module to stay in sync.
"""
from __future__ import annotations

import re

from django.contrib.auth.models import User
from django.db import models


# ─── Shared constants ──────────────────────────────────────────────────────────

class Role(models.TextChoices):
    ADMIN = 'admin', 'Administrator'
    IMAM  = 'imam',  'Bosh Imom'
    HODIM = 'hodim', 'Masjid Hodimi'


class MuhtojlikTuri(models.TextChoices):
    OZIQ_OVQAT = 'oziq_ovqat', "🍞 Oziq-ovqat"
    DORI       = 'dori',       "💊 Dori-darmon"
    IJARA      = 'ijara',      "🏠 Ijara/uy-joy"
    TOY        = 'toy',        "💒 To'y yordami"
    TAZIYA     = 'taziya',     "🕌 Ta'ziya"
    TALIM      = 'talim',      "📚 Ta'lim/maktab"
    KASALXONA  = 'kasalxona',  "🏥 Kasalxona/davolash"
    BOSHQA     = 'boshqa',     "📋 Boshqa"


class Priority(models.IntegerChoices):
    YUQORI = 1, "🔴 Yuqori — Tezkor yordam kerak"
    ORTA   = 2, "🟡 O'rta — Yaqin orada"
    PAST   = 3, "🟢 Past — Kechiktirilishi mumkin"


class Holat(models.TextChoices):
    YANGI         = 'yangi',             'Yangi'
    KORIB         = 'korib_chiqilmoqda', "Ko'rib chiqilmoqda"
    YORDAM        = 'yordam_berildi',    'Yordam berildi'
    RAD           = 'rad_etildi',        'Rad etildi'
    KECHIKTIRILDI = 'kechiktirildi',     'Kechiktirildi'


HOLAT_TERMINAL = {Holat.YORDAM, Holat.RAD}


class YordamTuri(models.TextChoices):
    PUL        = 'pul',        "💵 Pul"
    OZIQ_OVQAT = 'oziq_ovqat', "🍞 Oziq-ovqat"
    KIYIM      = 'kiyim',      "👕 Kiyim-kechak"
    DORI       = 'dori',       "💊 Dori-darmon"
    MAHSULOT   = 'mahsulot',   "📦 Mahsulot/jihoz"
    XIZMAT     = 'xizmat',     "🛠 Xizmat"
    BOSHQA     = 'boshqa',     "📋 Boshqa"


# ─── Helpers ───────────────────────────────────────────────────────────────────

_PHONE_DIGITS_RE = re.compile(r'\D+')


def normalize_phone(raw: str) -> str:
    """Normalize a phone number to a digits-only canonical form.

    Used both for storage and for lookups so equality is reliable.
    Empty input returns an empty string (validation happens at form level).
    """
    if not raw:
        return ''
    digits = _PHONE_DIGITS_RE.sub('', raw)
    # Cheap normalization for Uzbekistan numbers without country code
    if len(digits) == 9 and not digits.startswith('998'):
        digits = '998' + digits
    return digits


# ─── Models ────────────────────────────────────────────────────────────────────

class UserProfile(models.Model):
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role        = models.CharField(max_length=20, choices=Role.choices, default=Role.HODIM)
    telefon     = models.CharField(max_length=32, blank=True)
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True, verbose_name="Telegram ID")

    class Meta:
        verbose_name = "Profil"
        verbose_name_plural = "Profillar"

    def __str__(self) -> str:
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def is_imam(self) -> bool:
        return self.role == Role.IMAM

    @property
    def can_edit(self) -> bool:
        return self.role in {Role.ADMIN, Role.IMAM}

    @property
    def can_delete(self) -> bool:
        return self.role == Role.ADMIN


class Shaxs(models.Model):
    fio                = models.CharField(max_length=200, verbose_name="F.I.O")
    telefon            = models.CharField(max_length=32, unique=True, verbose_name="Telefon raqami")
    manzil             = models.CharField(max_length=300, blank=True, verbose_name="Manzil")
    qoshimcha_ma_lumot = models.TextField(blank=True, verbose_name="Qo'shimcha ma'lumot")
    yaratilgan         = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Shaxs"
        verbose_name_plural = "Shaxslar"
        ordering = ['fio']
        indexes = [
            models.Index(fields=['fio'], name='shaxs_fio_idx'),
        ]

    def __str__(self) -> str:
        return f"{self.fio} ({self.telefon})"

    def save(self, *args, **kwargs):
        # Always store phones in canonical form so lookups don't drift.
        self.telefon = normalize_phone(self.telefon)
        super().save(*args, **kwargs)

    @property
    def murojaatlar_soni(self) -> int:
        # Use the annotated count when available (set by views.shaxslar_list),
        # otherwise issue a fallback query.
        cached = getattr(self, 'murojaatlar_count', None)
        if cached is not None:
            return cached
        return self.murojaatlar.count()


class Murojaat(models.Model):
    # Re-exported so legacy callers and templates keep working.
    MUHTOJLIK_TURLARI = MuhtojlikTuri.choices
    PRIORITY_CHOICES  = Priority.choices
    HOLAT_CHOICES     = Holat.choices

    shaxs           = models.ForeignKey(Shaxs, on_delete=models.CASCADE, related_name='murojaatlar')
    muhtojlik_turi  = models.CharField(max_length=30, choices=MuhtojlikTuri.choices, db_index=True,
                                       verbose_name="Muhtojlik turi")
    mazmun          = models.TextField(verbose_name="Murojaat mazmuni")
    priority        = models.IntegerField(choices=Priority.choices, default=Priority.ORTA, db_index=True,
                                          verbose_name="Muhimlik darajasi")
    holat           = models.CharField(max_length=30, choices=Holat.choices, default=Holat.YANGI, db_index=True,
                                       verbose_name="Holat")

    murojaat_sanasi = models.DateField(db_index=True, verbose_name="Murojaat sanasi")
    yaratilgan      = models.DateTimeField(auto_now_add=True)
    yangilangan     = models.DateTimeField(auto_now=True)

    yordam_sanasi   = models.DateField(null=True, blank=True, verbose_name="Yordam berilgan sana")
    yordam_turi     = models.CharField(max_length=200, blank=True, verbose_name="Yordam turi")
    yordam_miqdori  = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True,
                                          verbose_name="Yordam miqdori (so'm)")
    mas_ul_hodim    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='boshqargan_murojaatlar', verbose_name="Mas'ul hodim")
    izoh            = models.TextField(blank=True, verbose_name="Izoh")

    telegram_id       = models.BigIntegerField(null=True, blank=True, db_index=True)
    telegram_username = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Murojaat"
        verbose_name_plural = "Murojaatlar"
        ordering = ['priority', '-murojaat_sanasi']
        indexes = [
            models.Index(fields=['holat', 'priority'],            name='mur_status_pri_idx'),
            models.Index(fields=['-murojaat_sanasi'],             name='mur_sanasi_desc_idx'),
            models.Index(fields=['holat', '-yaratilgan'],         name='mur_status_recent_idx'),
        ]

    def __str__(self) -> str:
        return f"{self.shaxs.fio} — {self.get_muhtojlik_turi_display()} ({self.murojaat_sanasi})"

    @property
    def is_from_telegram(self) -> bool:
        return self.telegram_id is not None

    @property
    def is_terminal(self) -> bool:
        return self.holat in HOLAT_TERMINAL

    @property
    def is_urgent(self) -> bool:
        return self.priority == Priority.YUQORI and not self.is_terminal


class Yordam(models.Model):
    """Konkret shaxsga berilgan yordam — pul, mahsulot, xizmat va h.k.

    Bir shaxsga ko'p kishidan yordam kelishi mumkin (1—N). Yordam
    aniq bir murojaatga bog'lanishi (`murojaat`) ham, umumiy bo'lishi
    ham mumkin — shuning uchun `murojaat` ixtiyoriy.
    """

    shaxs          = models.ForeignKey(Shaxs, on_delete=models.CASCADE,
                                       related_name='yordamlar',
                                       verbose_name="Yordam beriluvchi")
    murojaat       = models.ForeignKey(Murojaat, on_delete=models.SET_NULL,
                                       null=True, blank=True,
                                       related_name='yordamlar',
                                       verbose_name="Bog'liq murojaat")

    turi           = models.CharField(max_length=20, choices=YordamTuri.choices,
                                      default=YordamTuri.PUL, db_index=True,
                                      verbose_name="Yordam turi")
    miqdor         = models.DecimalField(max_digits=14, decimal_places=0,
                                         null=True, blank=True,
                                         verbose_name="Miqdor (so'm)",
                                         help_text="Pul bo'lsa — summa. Mahsulot bo'lsa — taxminiy qiymat (ixtiyoriy).")
    mazmun         = models.TextField(blank=True, verbose_name="Tavsif",
                                      help_text="Masalan: '5 kg sahar, 2L yog''.")

    bergan_fio     = models.CharField(max_length=200, verbose_name="Yordam bergan shaxs")
    bergan_telefon = models.CharField(max_length=32, blank=True, verbose_name="Telefon (ixtiyoriy)")

    sana           = models.DateField(db_index=True, verbose_name="Sana")
    qabul_qilgan   = models.ForeignKey(User, on_delete=models.SET_NULL,
                                       null=True, blank=True,
                                       related_name='qabul_qilgan_yordamlar',
                                       verbose_name="Qabul qilgan hodim")

    yaratilgan     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Yordam"
        verbose_name_plural = "Yordamlar"
        ordering = ['-sana', '-yaratilgan']
        indexes = [
            models.Index(fields=['shaxs', '-sana'], name='yordam_shaxs_sana_idx'),
            models.Index(fields=['-sana'],          name='yordam_sana_desc_idx'),
        ]

    def __str__(self) -> str:
        return f"{self.bergan_fio} → {self.shaxs.fio} ({self.sana})"

    def save(self, *args, **kwargs):
        if self.bergan_telefon:
            self.bergan_telefon = normalize_phone(self.bergan_telefon)
        super().save(*args, **kwargs)
