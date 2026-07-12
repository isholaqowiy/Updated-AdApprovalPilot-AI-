"""
AdApprovalPilot AI — entrypoint for Render Background Worker deployment.

Runs aiogram long-polling. No FastAPI, no webhook routes, no port binding —
Background Worker services on Render don't expose a public port, so
polling is the correct fit (same pattern as your other Render bots).
"""
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from database import init_models
from app.middleware.access_control import AccessControlMiddleware
from app.handlers import admin_handlers, user_handlers
from app.core.logger import get_logger

logger = get_logger(__name__)


async def main() -> None:
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # MemoryStorage is fine for a single Background Worker instance. If you
    # ever scale to multiple worker instances, swap in RedisStorage so FSM
    # state (mid-audit / mid-fix conversations) is shared across them.
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(AccessControlMiddleware())
    dp.callback_query.middleware(AccessControlMiddleware())

    dp.include_router(admin_handlers.router)
    dp.include_router(user_handlers.router)

    logger.info("Initializing database models...")
    await init_models()

    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Starting AdApprovalPilot AI (Background Worker / long-polling)...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
