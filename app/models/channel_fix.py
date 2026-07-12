"""Bot Fix Mode: per-channel authorization gate + applied-fix history."""
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class ChannelFix(Base):
    __tablename__ = "channel_fixes"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_identifier: Mapped[str] = mapped_column(String(256), unique=True)
    owner_id: Mapped[int] = mapped_column(BigInteger)

    is_fix_authorized: Mapped[bool] = mapped_column(Boolean, default=False)
    bot_is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    original_title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    original_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    new_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
