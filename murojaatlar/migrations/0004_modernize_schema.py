"""
Modernize the schema:

1. Re-introduce the full set of `muhtojlik_turi` choices (oziq_ovqat, dori,
   ijara, toy, taziya, talim, kasalxona, boshqa). Migration 0003 previously
   collapsed three of them into 'boshqa' to align with a temporary 5-type
   model; the canonical product spec is 8 types, so we just relax the choices
   list. (No data is rewritten — values are preserved as 'boshqa'; operators
   can re-categorise from the admin if needed.)

2. Normalize all stored phone numbers to a canonical digits-only form, then
   merge duplicate `Shaxs` rows by phone (the older row keeps its history;
   the newer ones' `Murojaat`s are reassigned to it before deletion).

3. Add `unique=True` to `Shaxs.telefon` so `get_or_create(telefon=...)` is
   actually safe under concurrent writes.

4. Add `unique=True` to `UserProfile.telegram_id` to prevent two operators
   sharing the same Telegram identity.

5. Add per-column indexes on the most-filtered fields and a few composite
   indexes for the dashboard / list queries.
"""
from __future__ import annotations

import re

from django.db import migrations, models


_PHONE_DIGITS_RE = re.compile(r'\D+')


def _canonical_phone(raw: str) -> str:
    if not raw:
        return ''
    digits = _PHONE_DIGITS_RE.sub('', raw)
    if len(digits) == 9 and not digits.startswith('998'):
        digits = '998' + digits
    return digits


def normalize_and_dedupe(apps, schema_editor):
    Shaxs = apps.get_model('murojaatlar', 'Shaxs')
    Murojaat = apps.get_model('murojaatlar', 'Murojaat')

    # Step 1: rewrite each row with the canonical phone (lets us spot dupes).
    for shaxs in Shaxs.objects.all():
        canonical = _canonical_phone(shaxs.telefon)
        if canonical != shaxs.telefon:
            shaxs.telefon = canonical
            shaxs.save(update_fields=['telefon'])

    # Step 2: merge duplicates. Keep the oldest row per canonical phone.
    seen: dict[str, int] = {}
    for shaxs in Shaxs.objects.exclude(telefon='').order_by('id'):
        keeper_id = seen.get(shaxs.telefon)
        if keeper_id is None:
            seen[shaxs.telefon] = shaxs.id
            continue
        Murojaat.objects.filter(shaxs_id=shaxs.id).update(shaxs_id=keeper_id)
        shaxs.delete()


def normalize_telegram_ids(apps, schema_editor):
    """If two profiles share a telegram_id, drop the duplicate (keep oldest)."""
    UserProfile = apps.get_model('murojaatlar', 'UserProfile')
    seen: set[int] = set()
    for profile in UserProfile.objects.exclude(telegram_id__isnull=True).order_by('id'):
        if profile.telegram_id in seen:
            profile.telegram_id = None
            profile.save(update_fields=['telegram_id'])
        else:
            seen.add(profile.telegram_id)


def noop(apps, schema_editor):
    """Reverse is intentionally a no-op — this migration is data-cleanup."""


class Migration(migrations.Migration):

    dependencies = [
        ('murojaatlar', '0003_update_model'),
    ]

    operations = [
        # ── 1. Data clean-up before tightening constraints ────────────────────
        migrations.RunPython(normalize_and_dedupe, noop),
        migrations.RunPython(normalize_telegram_ids, noop),

        # ── 2. Shaxs.telefon: widen + unique ──────────────────────────────────
        migrations.AlterField(
            model_name='shaxs',
            name='telefon',
            field=models.CharField(max_length=32, unique=True, verbose_name='Telefon raqami'),
        ),
        migrations.AddIndex(
            model_name='shaxs',
            index=models.Index(fields=['fio'], name='shaxs_fio_idx'),
        ),

        # ── 3. UserProfile: phone widen + telegram_id unique ──────────────────
        migrations.AlterField(
            model_name='userprofile',
            name='telefon',
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='telegram_id',
            field=models.BigIntegerField(blank=True, null=True, unique=True, verbose_name='Telegram ID'),
        ),

        # ── 4. Murojaat: relax muhtojlik_turi choices + indexes ───────────────
        migrations.AlterField(
            model_name='murojaat',
            name='muhtojlik_turi',
            field=models.CharField(
                choices=[
                    ('oziq_ovqat', '🍞 Oziq-ovqat'),
                    ('dori',       '💊 Dori-darmon'),
                    ('ijara',      '🏠 Ijara/uy-joy'),
                    ('toy',        "💒 To'y yordami"),
                    ('taziya',     "🕌 Ta'ziya"),
                    ('talim',      "📚 Ta'lim/maktab"),
                    ('kasalxona',  '🏥 Kasalxona/davolash'),
                    ('boshqa',     '📋 Boshqa'),
                ],
                db_index=True,
                max_length=30,
                verbose_name='Muhtojlik turi',
            ),
        ),
        migrations.AlterField(
            model_name='murojaat',
            name='priority',
            field=models.IntegerField(
                choices=[
                    (1, '🔴 Yuqori — Tezkor yordam kerak'),
                    (2, "🟡 O'rta — Yaqin orada"),
                    (3, '🟢 Past — Kechiktirilishi mumkin'),
                ],
                db_index=True,
                default=2,
                verbose_name='Muhimlik darajasi',
            ),
        ),
        migrations.AlterField(
            model_name='murojaat',
            name='holat',
            field=models.CharField(
                choices=[
                    ('yangi',             'Yangi'),
                    ('korib_chiqilmoqda', "Ko'rib chiqilmoqda"),
                    ('yordam_berildi',    'Yordam berildi'),
                    ('rad_etildi',        'Rad etildi'),
                    ('kechiktirildi',     'Kechiktirildi'),
                ],
                db_index=True,
                default='yangi',
                max_length=30,
                verbose_name='Holat',
            ),
        ),
        migrations.AlterField(
            model_name='murojaat',
            name='murojaat_sanasi',
            field=models.DateField(db_index=True, verbose_name='Murojaat sanasi'),
        ),
        migrations.AlterField(
            model_name='murojaat',
            name='telegram_id',
            field=models.BigIntegerField(blank=True, db_index=True, null=True),
        ),

        # ── 5. Composite indexes used by dashboard / list views ───────────────
        migrations.AddIndex(
            model_name='murojaat',
            index=models.Index(fields=['holat', 'priority'], name='mur_status_pri_idx'),
        ),
        migrations.AddIndex(
            model_name='murojaat',
            index=models.Index(fields=['-murojaat_sanasi'], name='mur_sanasi_desc_idx'),
        ),
        migrations.AddIndex(
            model_name='murojaat',
            index=models.Index(fields=['holat', '-yaratilgan'], name='mur_status_recent_idx'),
        ),
    ]
