"""User-facing command and callback handlers."""
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import settings
from database import get_session
from app.core.states import AuditStates, FixStates
from app.models.user import User
from app.models.audit import AuditLog
from app.services.audit_engine import run_channel_audit
from app.services.fix_engine import get_or_create_fix_record, apply_channel_fix
from app.core.logger import get_logger

router = Router(name="user_handlers")
logger = get_logger(__name__)

MAIN_MENU = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📊 Channel Index", callback_data="channel_index")],
        [InlineKeyboardButton(text="🔧 Allow Bot to Fix My Channel/Group", callback_data="fix_mode")],
    ]
)

REQUEST_ACCESS_KB = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="🔑 Request Admin Access", callback_data="request_access")]]
)


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User) -> None:
    if not db_user.is_approved:
        await message.answer(
            "🚫 Access Restricted\n\n"
            "AdApprovalPilot AI is an invite-only Telegram Ads compliance tool.\n"
            "Your access is currently pending approval.\n\n"
            f"Please contact admin: {settings.admin_handle}",
            reply_markup=REQUEST_ACCESS_KB,
        )
        return
    await message.answer(
        f"✅ Welcome back to AdApprovalPilot AI, {message.from_user.first_name}!\n"
        "Choose an action below:",
        reply_markup=MAIN_MENU,
    )


@router.callback_query(F.data == "request_access")
async def request_access(callback: CallbackQuery, bot: Bot, db_user: User) -> None:
    await callback.answer("Request sent to admin ✅")
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Approve", callback_data=f"approve:{db_user.id}"),
                InlineKeyboardButton(text="❌ Deny", callback_data=f"deny:{db_user.id}"),
            ],
            [
                InlineKeyboardButton(text="🚫 Disable", callback_data=f"disable:{db_user.id}"),
                InlineKeyboardButton(text="🔄 Reset Access", callback_data=f"reset:{db_user.id}"),
            ],
            [InlineKeyboardButton(text="🗑️ Remove From Channels", callback_data=f"remove_channels:{db_user.id}")],
        ]
    )
    await bot.send_message(
        settings.admin_id,
        "🔔 Access Request\n"
        f"👤 Name: {db_user.first_name}\n"
        f"🆔 ID: {db_user.id}\n"
        f"📛 Username: @{db_user.username}\n"
        "📊 Status: Pending",
        reply_markup=kb,
    )


@router.callback_query(F.data == "channel_index")
async def prompt_channel_link(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(AuditStates.waiting_for_channel)
    await callback.message.answer("Send me the channel username or invite link to audit (e.g. @yourchannel).")


@router.message(StateFilter(AuditStates.waiting_for_channel))
async def handle_channel_link(message: Message, bot: Bot, db_user: User, state: FSMContext) -> None:
    await state.clear()

    if db_user.role != "premium" and db_user.daily_scan_count >= settings.free_daily_scan_limit:
        await message.answer("⛔ Daily scan limit reached for free tier. Upgrade to premium for unlimited scans.")
        return

    status_msg = await message.answer(
        "🔍 AdApprovalPilot AI is fetching real data... Please wait while we run a full compliance check."
    )
    channel_identifier = message.text.strip()
    try:
        result = await run_channel_audit(bot, channel_identifier)
    except Exception as exc:
        logger.exception("Audit failed for %s", channel_identifier)
        await status_msg.edit_text(f"❌ Could not audit that channel: {exc}")
        return

    async with get_session() as session:
        session.add(
            AuditLog(
                requested_by=db_user.id,
                channel_identifier=channel_identifier,
                engagement_score=result.engagement,
                consistency_score=result.consistency,
                bio_score=result.bio,
                pinned_score=result.pinned,
                safety_score=result.safety,
                link_hygiene_score=result.link_hygiene,
                weighted_total=result.weighted_total,
                risk_level=result.risk_level,
                report_text=result.report_text,
            )
        )
        db_user.daily_scan_count += 1
        session.add(db_user)

    await status_msg.edit_text(result.report_text)


@router.callback_query(F.data == "fix_mode")
async def fix_mode_entry(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(FixStates.waiting_for_channel)
    await callback.message.answer(
        "🔧 Bot Fix Mode\n\n"
        "1️⃣ Add this bot as Admin to your channel (with rights to change info & edit/delete messages).\n"
        "2️⃣ Reply here with the channel username once done.\n\n"
        f"Note: channels must be pre-authorized by {settings.admin_handle} before fixes can run."
    )


@router.message(StateFilter(FixStates.waiting_for_channel))
async def handle_fix_channel(message: Message, bot: Bot, db_user: User, state: FSMContext) -> None:
    await state.clear()
    channel_identifier = message.text.strip()

    async with get_session() as session:
        fix = await get_or_create_fix_record(session, channel_identifier, db_user.id)

        if not fix.is_fix_authorized:
            await message.answer(
                "❌ This channel isn't authorized for Bot Fix Mode yet.\n"
                f"Please contact {settings.admin_handle} to enable it."
            )
            return

        try:
            member = await bot.get_chat_member(channel_identifier, bot.id)
            if member.status != "administrator":
                await message.answer(
                    "❌ The bot needs to be added as an Admin (with rights to change info) "
                    "before Fix Mode can run. Add it, then send the channel username again."
                )
                return
        except Exception as exc:
            await message.answer(f"❌ Couldn't verify bot admin status: {exc}")
            return

        status_msg = await message.answer("🔧 Analyzing channel and generating a compliant rewrite...")
        try:
            suggestion = await apply_channel_fix(bot, session, fix)
        except Exception as exc:
            logger.exception("Fix mode failed for %s", channel_identifier)
            await status_msg.edit_text(f"❌ Fix failed: {exc}")
            return

    posts_preview = "\n\n".join(f"📝 Sample Post {i+1}:\n{p}" for i, p in enumerate(suggestion.mock_posts))
    await status_msg.edit_text(
        "✅ Channel updated!\n\n"
        f"New Title: {suggestion.optimized_title}\n"
        f"New Description: {suggestion.optimized_description}\n\n"
        f"Why: {suggestion.rationale}\n\n"
        f"{posts_preview}"
        )
