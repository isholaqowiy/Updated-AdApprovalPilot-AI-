"""Admin-only command and callback handlers."""
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from config import settings
from database import get_session
from app.core.security import is_admin
from app.models.user import User
from app.models.channel_fix import ChannelFix
from app.core.logger import get_logger

router = Router(name="admin_handlers")
logger = get_logger(__name__)


@router.callback_query(F.data.startswith("approve:"))
async def approve_user(callback: CallbackQuery, bot: Bot) -> None:
    if not is_admin(callback.from_user.id):
        return await callback.answer("Not authorized.", show_alert=True)
    target_id = int(callback.data.split(":")[1])
    async with get_session() as session:
        result = await session.execute(select(User).where(User.id == target_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_approved = True
            user.is_disabled = False
            session.add(user)
    await callback.answer("Approved ✅")
    await callback.message.edit_text(callback.message.text + "\n\n✅ APPROVED")
    await bot.send_message(target_id, "✅ Access Approved!\nWelcome to AdApprovalPilot AI. Send /start to begin.")


@router.callback_query(F.data.startswith("deny:"))
async def deny_user(callback: CallbackQuery, bot: Bot) -> None:
    if not is_admin(callback.from_user.id):
        return await callback.answer("Not authorized.", show_alert=True)
    target_id = int(callback.data.split(":")[1])
    await callback.answer("Denied ❌")
    await callback.message.edit_text(callback.message.text + "\n\n❌ DENIED")
    await bot.send_message(target_id, f"❌ Your access request was denied. Contact {settings.admin_handle} for details.")


@router.callback_query(F.data.startswith("disable:"))
async def disable_user(callback: CallbackQuery, bot: Bot) -> None:
    if not is_admin(callback.from_user.id):
        return await callback.answer("Not authorized.", show_alert=True)
    target_id = int(callback.data.split(":")[1])
    async with get_session() as session:
        result = await session.execute(select(User).where(User.id == target_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_disabled = True
            session.add(user)
    await callback.answer("Disabled 🚫")
    await callback.message.edit_text(callback.message.text + "\n\n🚫 DISABLED")
    await bot.send_message(target_id, f"🚫 Your access has been disabled. Contact {settings.admin_handle}.")


@router.callback_query(F.data.startswith("reset:"))
async def reset_user(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return await callback.answer("Not authorized.", show_alert=True)
    target_id = int(callback.data.split(":")[1])
    async with get_session() as session:
        result = await session.execute(select(User).where(User.id == target_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_disabled = False
            user.is_approved = False
            user.daily_scan_count = 0
            session.add(user)
    await callback.answer("Access reset 🔄")
    await callback.message.edit_text(callback.message.text + "\n\n🔄 RESET")


@router.callback_query(F.data.startswith("remove_channels:"))
async def remove_from_channels(callback: CallbackQuery, bot: Bot) -> None:
    if not is_admin(callback.from_user.id):
        return await callback.answer("Not authorized.", show_alert=True)
    target_id = int(callback.data.split(":")[1])
    async with get_session() as session:
        result = await session.execute(select(ChannelFix).where(ChannelFix.owner_id == target_id))
        fixes = result.scalars().all()
        for fix in fixes:
            try:
                await bot.leave_chat(fix.channel_identifier)
            except Exception:
                logger.warning("Could not leave chat %s", fix.channel_identifier)
    await callback.answer("Bot removed from user's channels 🗑️")


@router.message(Command("authorize_fix"))
async def authorize_fix(message: Message) -> None:
    """Usage: /authorize_fix @channelusername owner_telegram_id"""
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Usage: /authorize_fix @channel owner_id")
        return
    channel, owner_id = parts[1], int(parts[2])
    async with get_session() as session:
        result = await session.execute(select(ChannelFix).where(ChannelFix.channel_identifier == channel))
        fix = result.scalar_one_or_none()
        if fix is None:
            fix = ChannelFix(channel_identifier=channel, owner_id=owner_id)
        fix.is_fix_authorized = True
        session.add(fix)
    await message.answer(f"✅ {channel} authorized for Bot Fix Mode.")


@router.message(Command("force_remove_bot"))
async def force_remove_bot(message: Message, bot: Bot) -> None:
    """Usage: /force_remove_bot @channelusername — global override to exit any client channel."""
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: /force_remove_bot @channel")
        return
    try:
        await bot.leave_chat(parts[1])
        await message.answer(f"✅ Left {parts[1]}.")
    except Exception as exc:
        await message.answer(f"❌ Failed: {exc}")


@router.message(Command("set_premium"))
async def set_premium(message: Message) -> None:
    """Usage: /set_premium user_id [invoice_id]"""
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /set_premium user_id [invoice_id]")
        return
    target_id = int(parts[1])
    invoice_id = parts[2] if len(parts) > 2 else None
    async with get_session() as session:
        result = await session.execute(select(User).where(User.id == target_id))
        user = result.scalar_one_or_none()
        if user:
            user.role = "premium"
            user.payment_status = "paid"
            user.invoice_id = invoice_id
            session.add(user)
    await message.answer(f"✅ User {target_id} upgraded to premium.")
