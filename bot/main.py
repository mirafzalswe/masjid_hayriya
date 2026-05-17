"""
Masjid Xayriya — Telegram Bot (aiogram 3 + FastAPI)
====================================================

Ishga tushirish:
    uvicorn bot.main:app --host 0.0.0.0 --port 8001 --reload

Webhook sozlash (botni internetga ulash uchun):
    https://api.telegram.org/bot{TOKEN}/setWebhook?url=https://your-domain.com/webhook

Local ishlab chiqish uchun (polling rejimi):
    python -m bot.polling
"""

import os
import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update

from .db import setup_django
from .handlers import router

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

# ─── Config ──────────────────────────────────────────────────────────────────
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
WEBHOOK_PATH = "/webhook"
# Required for webhook mode. An empty value disables signature checking,
# which is acceptable for local testing only.
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

# ─── Bot va Dispatcher ───────────────────────────────────────────────────────
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)


# ─── FastAPI lifespan ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ishga tushganda
    setup_django()
    log.info("Django ORM ulandi")

    if not TOKEN:
        log.error("TELEGRAM_TOKEN topilmadi! .env faylni tekshiring.")
    else:
        me = await bot.get_me()
        log.info(f"Bot: @{me.username} ({me.id})")

    yield

    # To'xtaganda
    await bot.session.close()
    log.info("Bot to'xtatildi")


# ─── FastAPI app ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="Masjid Xayriya Bot",
    lifespan=lifespan,
)


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request) -> Response:
    """Telegram dan kelgan update larni qabul qiladi"""
    # Secret header tekshirish (xavfsizlik uchun)
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if WEBHOOK_SECRET and secret != WEBHOOK_SECRET:
        log.warning(f"Noto'g'ri secret: {secret!r}")
        return Response(status_code=403)

    body = await request.json()
    update = Update.model_validate(body)
    await dp.feed_update(bot=bot, update=update)
    return Response(status_code=200)


@app.get("/")
async def health():
    return {"status": "ok", "service": "Masjid Xayriya Bot"}


@app.get("/set-webhook")
async def set_webhook(url: str):
    """
    Webhookni o'rnatish:
    GET /set-webhook?url=https://your-domain.com/webhook
    """
    result = await bot.set_webhook(
        url=f"{url}{WEBHOOK_PATH}",
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True,
    )
    info = await bot.get_webhook_info()
    return {
        "ok": result,
        "webhook_url": info.url,
        "pending_updates": info.pending_update_count,
    }


@app.get("/delete-webhook")
async def delete_webhook():
    """Webhookni o'chirish (polling rejimiga o'tish uchun)"""
    result = await bot.delete_webhook(drop_pending_updates=True)
    return {"ok": result}
