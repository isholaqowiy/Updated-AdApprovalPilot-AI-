"""Pydantic schemas that constrain and validate structured Gemini outputs."""
from pydantic import BaseModel, Field


class ChannelFixSuggestion(BaseModel):
    optimized_title: str = Field(..., description="Compliant, optimized channel title")
    optimized_description: str = Field(..., description="Compliant, optimized channel description/bio")
    mock_posts: list[str] = Field(..., min_length=3, max_length=3, description="3 mock compliant broadcast posts")
    rationale: str = Field(..., description="Short rationale for the changes made")


class ChannelAuditInsights(BaseModel):
    risk_level: str = Field(..., description="LOW, MEDIUM, or HIGH")
    summary: str
    optimization_points: list[str]
