"""
Async Gemini API integration.

Uses structured JSON output mode so responses parse directly into the
Pydantic schemas in app/schemas/ai_schema.py without brittle regex/text
parsing — this is what lets Bot Fix Mode safely apply edits live.
"""
import json

from google import genai
from google.genai import types

from config import settings
from app.schemas.ai_schema import ChannelFixSuggestion, ChannelAuditInsights
from app.core.logger import get_logger

logger = get_logger(__name__)

_client = genai.Client(api_key=settings.gemini_api_key)


async def generate_channel_fix(
    title: str, description: str, recent_posts: list[str]
) -> ChannelFixSuggestion:
    prompt = (
        "You are a Telegram Ads compliance specialist. Given the channel data "
        "below, produce a fully compliant, non-clickbait, non-misleading title "
        "and description, plus 3 example broadcast posts that would pass "
        "Telegram Ads policy review.\n\n"
        f"Current title: {title}\n"
        f"Current description: {description}\n"
        f"Recent posts: {json.dumps(recent_posts[:10])}\n\n"
        "Respond ONLY with valid JSON matching this schema: "
        '{"optimized_title": str, "optimized_description": str, '
        '"mock_posts": [str, str, str], "rationale": str}'
    )
    response = await _client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    data = json.loads(response.text)
    return ChannelFixSuggestion(**data)


async def generate_audit_insights(channel_identifier: str, raw_metrics: dict) -> ChannelAuditInsights:
    prompt = (
        "You are auditing a Telegram channel for Telegram Ads compliance risk. "
        f"Channel: {channel_identifier}\nRaw metrics: {json.dumps(raw_metrics)}\n\n"
        "Respond ONLY with valid JSON: "
        '{"risk_level": "LOW|MEDIUM|HIGH", "summary": str, "optimization_points": [str, ...]}'
    )
    response = await _client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    data = json.loads(response.text)
    return ChannelAuditInsights(**data)
