"""Channel audit log model — one row per compliance scan."""
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    requested_by: Mapped[int] = mapped_column(BigInteger)
    channel_identifier: Mapped[str] = mapped_column(String(256))

    engagement_score: Mapped[float] = mapped_column(Float, default=0.0)
    consistency_score: Mapped[float] = mapped_column(Float, default=0.0)
    bio_score: Mapped[float] = mapped_column(Float, default=0.0)
    pinned_score: Mapped[float] = mapped_column(Float, default=0.0)
    safety_score: Mapped[float] = mapped_column(Float, default=0.0)
    link_hygiene_score: Mapped[float] = mapped_column(Float, default=0.0)

    weighted_total: Mapped[float] = mapped_column(Float, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    report_text: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
