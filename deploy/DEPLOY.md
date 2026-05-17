# Masjid Xayriya — Deploy на 139.59.130.53

HTTP-only, без домена. Доступ по IP. Стек: **Nginx → Gunicorn (Django)** + отдельный **systemd** для Telegram-бота.

```
Брauzer → http://139.59.130.53/   →  Nginx :80
                                       ├── /static/ → файлы напрямую
                                       └── /        → Gunicorn 127.0.0.1:8000
                                                       └── Django + SQLite

(параллельно) Telegram → bot/polling.py  (исходящий polling, портов не открывает)
```

---

## 1. На локальной машине — закинуть код на сервер

```bash
# Из корня проекта (~/Desktop/masjid_hayria)
rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.git' \
           --exclude 'db.sqlite3-shm' --exclude 'db.sqlite3-wal' \
      ./  root@139.59.130.53:/opt/masjid_hayria/
```

Если есть локальная БД с тестовыми данными — она тоже зальётся через `db.sqlite3`. Для чистого старта можно `rm /opt/masjid_hayria/db.sqlite3` на сервере и потом `migrate` сам создаст.

---

## 2. На сервере — подложить `.env`

```bash
ssh root@139.59.130.53
cd /opt/masjid_hayria
cp deploy/.env.production.example .env
nano .env     # проверить TELEGRAM_TOKEN
chmod 600 .env
```

Что внутри (готовый шаблон уже есть):
- `SECRET_KEY=…` — уже сгенерирован
- `DEBUG=False`
- `ALLOWED_HOSTS=139.59.130.53,localhost,127.0.0.1`
- `CSRF_TRUSTED_ORIGINS=http://139.59.130.53`
- `SECURE_SSL_REDIRECT=False` ← важно, HTTP-only
- `TELEGRAM_TOKEN=…`

---

## 3. На сервере — один скрипт-установщик

```bash
cd /opt/masjid_hayria
sudo bash deploy/setup.sh
```

Скрипт сам:
1. Поставит `python3-venv`, `nginx`, `sqlite3`
2. Создаст venv, установит requirements
3. Применит миграции, соберёт static
4. Скопирует Nginx-конфиг + сделает symlink (отключит default-сайт на :80)
5. Установит и запустит **2 systemd-сервиса**: `masjid-web`, `masjid-bot`

В конце покажет статус. Открывайте **http://139.59.130.53/** — должна появиться страница логина.

---

## 4. Первый суперюзер (если БД чистая)

```bash
cd /opt/masjid_hayria
sudo -u www-data .venv/bin/python manage.py createsuperuser
```

Демо-пользователи `admin/admin`, `hodim/hodim`, `viewer/viewer` создаются автоматически миграцией `0002_demo_users` (если БД чистая). Для production их надо **сменить** или удалить.

---

## 5. Обновление кода в будущем

```bash
# Локально
rsync -avz --exclude '.venv' --exclude '__pycache__' \
           --exclude 'db.sqlite3*' --exclude '.env' \
      ./ root@139.59.130.53:/opt/masjid_hayria/

# На сервере
ssh root@139.59.130.53 '
  cd /opt/masjid_hayria &&
  .venv/bin/pip install -r requirements.txt &&
  .venv/bin/python manage.py migrate --noinput &&
  .venv/bin/python manage.py collectstatic --noinput &&
  systemctl restart masjid-web masjid-bot
'
```

---

## 6. Управление

| Команда | Что делает |
|---|---|
| `systemctl status masjid-web` | состояние веб-сервера |
| `systemctl status masjid-bot` | состояние бота |
| `journalctl -u masjid-web -f` | логи Django в реальном времени |
| `journalctl -u masjid-bot -f` | логи бота |
| `systemctl restart masjid-web` | перезапуск веб после обновления |
| `systemctl restart masjid-bot` | перезапуск бота |
| `nginx -t && systemctl reload nginx` | перечитать конфиг Nginx |

---

## 7. Бэкап БД

SQLite — один файл. Раз в день копировать (cron):

```bash
# /etc/cron.daily/masjid-backup
#!/bin/bash
set -e
ts=$(date +%F)
mkdir -p /var/backups/masjid
sqlite3 /opt/masjid_hayria/db.sqlite3 ".backup '/var/backups/masjid/db-$ts.sqlite3'"
find /var/backups/masjid -name 'db-*.sqlite3' -mtime +14 -delete
```

```bash
sudo chmod +x /etc/cron.daily/masjid-backup
```

---

## 8. Файрвол (минимум)

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx HTTP'    # :80
sudo ufw enable
```

Порт 8000 (Gunicorn) только на `127.0.0.1` — извне недоступен. Так и должно быть.

---

## ⚠ Важно про HTTP

- Сайт работает по обычному HTTP (нет HTTPS, потому что нет домена для Let's Encrypt).
- Пароли передаются в открытом виде — для интранет/малой команды это приемлемо, но если позже появится домен → запустите `certbot --nginx -d вашдомен`, и в `.env` поставьте `SECURE_SSL_REDIRECT=True`, `USE_X_FORWARDED_PROTO=True`, `CSRF_TRUSTED_ORIGINS=https://вашдомен`.
- Telegram-бот работает в **polling** — он сам ходит к Telegram, входящих соединений не требует. Webhook не нужен.
