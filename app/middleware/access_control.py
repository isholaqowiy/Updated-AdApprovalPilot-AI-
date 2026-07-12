"""
Global aiogram middleware enforcing invite-only, multi-tier gatekeeping.

Runs on every incoming Message and CallbackQuery. Loads (or creates) the
User row, attaches it to handler data as `db_user`, and blocks all input
from unapproved/disabled accounts except /start and callback taps (needed
so the "Request Admin Access" button still works pre-approval).
"""
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy import select

from config import settings
from database import get_session
from app.models.user import User

ALLOWED_COMMANDS_WHEN_UNAPPROVED = {"/start"}


class AccessControlMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user is None:
            return await handler(event, data)

        async with get_session() as session:
            result = await session.execute(select(User).where(User.id == tg_user.id))
            user = result.scalar_one_or_none()

            if user is None:
                user = User(id=tg_user.id, username=tg_user.username, first_name=tg_user.first_name)
                session.add(user)
                await session.flush()

            data["db_user"] = user

            if user.id == settings.admin_id:
                return await handler(event, data)

            if user.is_disabled:
                await self._deny(
                    event,
                    f"🚫 Your access has been disabled. Contact {settings.admin_handle} for reinstatement.",
                )
                return None

            if not user.is_approved:
                if isinstance(event, Message) and (event.text or "") in ALLOWED_COMMANDS_WHEN_UNAPPROVED:
                    return await handler(event, data)
                if isinstance(event, CallbackQuery):
                    return await handler(event, data)
                await self._deny(
                    event,
                    "🚫 Access Restricted\n\n"
                    "AdApprovalPilot AI is an invite-only Telegram Ads compliance tool.\n"
                    "Your access is currently pending approval.\n\n"
                    f"Please contact admin: {settings.admin_handle}",
                )
                return None

            now = datetime.now(timezone.utc)
            last_reset = user.last_scan_reset
            if last_reset.tzinfo is None:
                last_reset = last_reset.replace(tzinfo=timezone.utc)
            if (now - last_reset).total_seconds() > 86400:
                user.daily_scan_count = 0
                user.last_scan_reset = now
                session.add(user)

            return await handler(event, data)

    @staticmethod
    async def _deny(event: TelegramObject, text: str) -> None:
        if isinstance(event, Message):
            await event.answer(text)
        elif isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)
