"""
Local ishlab chiqish uchun polling rejimi.
Internet (webhook) shart emas.

Ishga tushirish:
    python -m bot.polling
"""

import os
import asyncio
import logging

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from .db import setup_django
from .handlers import router

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


async def main():
    TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
    if not TOKEN:
        log.error("=" * 50)
        log.error("TELEGRAM_TOKEN topilmadi!")
        log.error("Quyidagilardan birini bajaring:")
        log.error("  1) export TELEGRAM_TOKEN='your_token'")
        log.error("  2) .env faylga yozing: TELEGRAM_TOKEN=your_token")
        log.error("=" * 50)
        return

    # Django ORM ni ulash
    setup_django()
    log.info("Django ORM ulandi")

    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    # Eski webhookni o'chirish
    await bot.delete_webhook(drop_pending_updates=True)

    me = await bot.get_me()
    log.info(f"✅ Bot ishga tushdi: @{me.username}")
    log.info("To'xtatish uchun Ctrl+C bosing")

    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        await bot.session.close()
        log.info("Bot to'xtatildi")


if __name__ == "__main__":
    asyncio.run(main())
