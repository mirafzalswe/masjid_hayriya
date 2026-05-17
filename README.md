# 🕌 Masjid Xayriya — Boshqaruv Tizimi

Masjidga murojaat qilgan nochor kishilarning ma'lumotlarini boshqarish uchun
Django web ilovasi va aiogram 3 + FastAPI Telegram boti.

---

## ⚡ Tez ishga tushirish

```bash
python --version    # 3.10+
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env  # qiymatlarini to'ldiring

python manage.py migrate
python manage.py runserver
# http://localhost:8000
```

### Demo hisoblar (faqat development uchun)

`migrations/0002_demo_users.py` quyidagi foydalanuvchilarni avtomatik yaratadi:

| Foydalanuvchi | Parol  | Rol            |
|---------------|--------|----------------|
| `admin`       | admin  | Administrator  |
| `hodim`       | hodim  | Bosh Imom      |
| `viewer`      | viewer | Hodim          |

Production uchun ularni o'chiring va o'zingizning admin foydalanuvchingizni
yarating: `python manage.py createsuperuser`.

---

## 🤖 Telegram Bot

`bot/` paketi aiogram 3 + FastAPI da yozilgan. Faqat ro'yxatga olingan
hodimlar (`UserProfile.telegram_id` to'ldirilganlar) botdan foydalana oladi.

### Local (polling, internet shart emas)

```bash
export TELEGRAM_TOKEN='your_token'
python -m bot.polling
```

### Production (webhook)

```bash
export TELEGRAM_TOKEN='your_token'
export WEBHOOK_SECRET='strong-random-string'
uvicorn bot.main:app --host 0.0.0.0 --port 8001
```

Webhookni o'rnatish:

```
GET /set-webhook?url=https://your-domain.com
```

---

## 👥 Rollar

| Rol            | Ko'rish | Qo'shish | Tahrirlash | O'chirish | Userlar |
|----------------|---------|----------|------------|-----------|---------|
| Administrator  | ✅      | ✅       | ✅         | ✅        | ✅      |
| Bosh Imom      | ✅      | ✅       | ✅         | ❌        | ❌      |
| Hodim          | ✅      | ❌       | ❌         | ❌        | ❌      |

---

## 🗂 Struktura

```
masjid_hayria/
├─ manage.py
├─ requirements.txt
├─ .env.example
├─ masjid_hayria/         # settings.py, urls.py
├─ murojaatlar/           # asosiy domen (models, views, forms, permissions)
│  ├─ models.py           # Role, MuhtojlikTuri, Priority, Holat enumlari
│  ├─ permissions.py      # admin_required, can_edit_required dekoratorlari
│  ├─ views.py            # auth · dashboard · CRUD
│  └─ migrations/0004_modernize_schema.py  # indekslar, unique constraint
├─ bot/                   # aiogram 3 + FastAPI bot
│  ├─ main.py             # FastAPI webhook
│  ├─ polling.py          # local development
│  ├─ handlers.py         # FSM
│  └─ db.py               # Django ORM async-helperlar
├─ templates/             # base.html va sahifalar
└─ static/css/style.css   # design system v4
```

---

## 🗄 Ma'lumotlar modeli

**Shaxs**: `fio`, `telefon` (unique, normalized), `manzil`, `qoshimcha_ma_lumot`.

**Murojaat**: `shaxs` (FK), `muhtojlik_turi` (8 ta tur), `mazmun`,
`priority` (1–3), `holat` (5 holat), `murojaat_sanasi`, yordam ma'lumotlari,
`telegram_id`, `telegram_username`.

**UserProfile**: `user` (OneToOne), `role`, `telefon`, `telegram_id` (unique).

---

## 🔒 Production xavfsizlik

`DEBUG=False` rejimida `settings.py` quyidagilarni majbur qiladi:

- `SECRET_KEY` muhit o'zgaruvchisidan olinishi (yo'q bo'lsa — `RuntimeError`).
- `ALLOWED_HOSTS` to'liq ko'rsatilgan bo'lishi.
- HSTS, secure cookies, SSL redirect (USE_SSL_REDIRECT=true bo'lsa).
- `CSRF_TRUSTED_ORIGINS` (CSRF_TRUSTED_ORIGINS=https://...).

---

*Alloh barchangizning xayr-ehsonlarini qabul qilsin. 🤲*
