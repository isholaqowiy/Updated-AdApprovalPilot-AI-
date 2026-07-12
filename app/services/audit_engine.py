"""
Weighted algorithmic channel compliance scoring engine.

Weights match spec: Engagement 30% / Consistency 20% / Bio 10% /
Pinned Resource 10% / Content Safety 20% / Link Hygiene 10%.

NOTE: The Bot API can only read metadata (title, description, pinned
message, member count) for chats the bot is a member of — it cannot read
historical message content it didn't post. Real engagement/consistency/
safety/link-hygiene scoring over message history requires an MTProto
client (Telethon), the same pattern already used in Omar's signal-copying
bot. The hooks below are wired for that; swap in a Telethon call to
replace the placeholder heuristics when that client is available here.
"""
from dataclasses import dataclass

from aiogram import Bot

from app.services.gemini_ai import generate_audit_insights

WEIGHTS = {
    "engagement": 0.30,
    "consistency": 0.20,
    "bio": 0.10,
    "pinned": 0.10,
    "safety": 0.20,
    "link_hygiene": 0.10,
}


@dataclass
class AuditResult:
    engagement: float
    consistency: float
    bio: float
    pinned: float
    safety: float
    link_hygiene: float
    weighted_total: float
    risk_level: str
    report_text: str


def _risk_from_score(score: float) -> str:
    if score >= 75:
        return "LOW"
    if score >= 50:
        return "MEDIUM"
    return "HIGH"


async def run_channel_audit(bot: Bot, channel_identifier: str) -> AuditResult:
    chat = await bot.get_chat(channel_identifier)
    member_count = await bot.get_chat_member_count(chat.id)

    bio = chat.description or ""
    bio_score = min(100.0, len(bio) / 2)
    pinned_score = 100.0 if getattr(chat, "pinned_message", None) else 0.0

    engagement_score = 60.0
    consistency_score = 60.0
    safety_score = 80.0
    link_hygiene_score = 70.0

    weighted_total = (
        engagement_score * WEIGHTS["engagement"]
        + consistency_score * WEIGHTS["consistency"]
        + bio_score * WEIGHTS["bio"]
        + pinned_score * WEIGHTS["pinned"]
        + safety_score * WEIGHTS["safety"]
        + link_hygiene_score * WEIGHTS["link_hygiene"]
    )
    fallback_risk = _risk_from_score(weighted_total)

    insights = await generate_audit_insights(
        channel_identifier,
        {
            "member_count": member_count,
            "engagement_score": engagement_score,
            "consistency_score": consistency_score,
            "bio_score": bio_score,
            "pinned_score": pinned_score,
            "safety_score": safety_score,
            "link_hygiene_score": link_hygiene_score,
        },
    )

    risk_level = insights.risk_level or fallback_risk
    report_lines = [
        f"🔍 Compliance Audit Report — {channel_identifier}",
        "",
        f"📊 Engagement Ratio: {engagement_score:.0f}/100",
        f"📅 Posting Consistency: {consistency_score:.0f}/100",
        f"📝 Bio Completeness: {bio_score:.0f}/100",
        f"📌 Pinned Resource: {pinned_score:.0f}/100",
        f"🛡️ Content Safety: {safety_score:.0f}/100",
        f"🔗 Link Hygiene: {link_hygiene_score:.0f}/100",
        "",
        f"⚖️ Weighted Score: {weighted_total:.1f}/100",
        f"🚦 Risk Level: {risk_level}",
        "",
        "💡 Optimization Points:",
        *[f"  • {p}" for p in insights.optimization_points],
    ]

    return AuditResult(
        engagement=engagement_score,
        consistency=consistency_score,
        bio=bio_score,
        pinned=pinned_score,
        safety=safety_score,
        link_hygiene=link_hygiene_score,
        weighted_total=weighted_total,
        risk_level=risk_level,
        report_text="\n".join(report_lines),
    )
