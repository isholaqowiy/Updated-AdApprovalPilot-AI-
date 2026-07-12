"""Applies AI-generated compliance fixes directly to a Telegram channel."""
from datetime import datetime, timezone

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel_fix import ChannelFix
from app.schemas.ai_schema import ChannelFixSuggestion
from app.services.gemini_ai import generate_channel_fix
from app.core.logger import get_logger

logger = get_logger(__name__)


async def get_or_create_fix_record(
    session: AsyncSession, channel_identifier: str, owner_id: int
) -> ChannelFix:
    result = await session.execute(
        select(ChannelFix).where(ChannelFix.channel_identifier == channel_identifier)
    )
    fix = result.scalar_one_or_none()
    if fix is None:
        fix = ChannelFix(channel_identifier=channel_identifier, owner_id=owner_id)
        session.add(fix)
        await session.flush()
    return fix


async def apply_channel_fix(bot: Bot, session: AsyncSession, fix: ChannelFix) -> ChannelFixSuggestion:
    chat = await bot.get_chat(fix.channel_identifier)
    recent_posts: list[str] = []

    suggestion = await generate_channel_fix(
        title=chat.title or "",
        description=chat.description or "",
        recent_posts=recent_posts,
    )

    fix.original_title = chat.title
    fix.original_description = chat.description
    fix.new_title = suggestion.optimized_title
    fix.new_description = suggestion.optimized_description

    await bot.set_chat_title(chat.id, suggestion.optimized_title[:128])
    await bot.set_chat_description(chat.id, suggestion.optimized_description[:255])

    fix.applied_at = datetime.now(timezone.utc)
    fix.bot_is_admin = True
    session.add(fix)

    logger.info("Applied compliance fix to %s", fix.channel_identifier)
    return suggestion
