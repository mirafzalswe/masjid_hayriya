#!/usr/bin/env bash
# Masjid Xayriya — birinchi marta server sozlash skripti.
# Ubuntu/Debian uchun. root yoki sudo bilan ishga tushiring.
#
# Foydalanish:
#   bash deploy/setup.sh
#
# Bu skript:
#   1) Tizim paketlarini o'rnatadi (python3.12, pip, venv, nginx, sqlite)
#   2) /opt/masjid_hayria ga virtualenv yaratadi va requirements'ni o'rnatadi
#   3) collectstatic, migrate qiladi
#   4) Nginx config va systemd service'larni joylashtiradi
#   5) Servislarni ishga tushiradi

set -euo pipefail

APP_DIR=/opt/masjid_hayria
USER=www-data

if [[ $EUID -ne 0 ]]; then
   echo "Bu skriptni root yoki sudo bilan ishga tushiring." >&2
   exit 1
fi

if [[ ! -f "$APP_DIR/manage.py" ]]; then
    echo "❌ $APP_DIR/manage.py topilmadi. Avval kodni $APP_DIR ga ko'chiring." >&2
    exit 1
fi

if [[ ! -f "$APP_DIR/.env" ]]; then
    echo "❌ $APP_DIR/.env topilmadi. deploy/.env.production'ni $APP_DIR/.env ga ko'chiring." >&2
    exit 1
fi

echo "═══ 1/6 Tizim paketlari ═══"
apt-get update -qq
apt-get install -y python3 python3-venv python3-pip nginx sqlite3

echo "═══ 2/6 Virtualenv va dependencies ═══"
cd "$APP_DIR"
if [[ ! -d .venv ]]; then
    python3 -m venv .venv
fi
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "═══ 3/6 collectstatic + migrate ═══"
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput

echo "═══ 4/6 Egalik (chown $USER:$USER) ═══"
chown -R $USER:$USER "$APP_DIR"
chmod 600 "$APP_DIR/.env"
# SQLite va WAL fayllariga yozish huquqi
chmod 660 "$APP_DIR/db.sqlite3" 2>/dev/null || true
chmod g+w "$APP_DIR"

echo "═══ 5/6 Nginx ═══"
cp deploy/nginx.conf /etc/nginx/sites-available/masjid_hayria
ln -sf /etc/nginx/sites-available/masjid_hayria /etc/nginx/sites-enabled/masjid_hayria
# Default Nginx sayti — o'chirish (port 80 da kollziya bo'lmasligi uchun)
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "═══ 6/6 Systemd servislari ═══"
cp deploy/masjid-web.service /etc/systemd/system/
cp deploy/masjid-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now masjid-web
systemctl enable --now masjid-bot

sleep 2
echo
echo "═══ Status ═══"
systemctl --no-pager status masjid-web --lines=5 || true
echo
systemctl --no-pager status masjid-bot --lines=5 || true

echo
echo "✅ Tayyor! Brauzerda oching: http://139.59.130.53/"
echo "   Loglar:  journalctl -u masjid-web -f"
echo "            journalctl -u masjid-bot -f"
