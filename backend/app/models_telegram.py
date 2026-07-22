import enum
from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .db import Base

if TYPE_CHECKING:
    from .models import Note, User


class ReminderDeliveryStatus(enum.StrEnum):
    pending = "pending"
    processing = "processing"
    sent = "sent"
    failed = "failed"
    cancelled = "cancelled"


class TelegramSettings(Base):
    __tablename__ = "telegram_settings"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    chat_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        unique=True,
    )

    username: Mapped[str | None] = mapped_column(String(64), nullable=True)

    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="UTC",
        server_default="UTC",
    )

    reminder_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        default=time(9, 0),
        server_default="09:00:00",
    )

    link_code: Mapped[str | None] = mapped_column(
        String(6),
        nullable=True,
        unique=True,
    )

    link_code_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="telegram_settings")


class NoteReminderDelivery(Base):
    __tablename__ = "note_reminder_deliveries"

    __table_args__ = (
        UniqueConstraint(
            "note_id",
            "scheduled_for",
            name="uq_note_reminder_delivery_note_scheduled_for",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    note_id: Mapped[int] = mapped_column(
        ForeignKey("notes.id", ondelete="CASCADE"),
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )

    status: Mapped[ReminderDeliveryStatus] = mapped_column(
        Enum(
            ReminderDeliveryStatus,
            name="reminder_delivery_status",
        ),
        nullable=False,
        default=ReminderDeliveryStatus.pending,
        server_default=ReminderDeliveryStatus.pending.value,
        index=True,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    note: Mapped["Note"] = relationship(back_populates="reminder_deliveries")
    user: Mapped["User"] = relationship(back_populates="reminder_deliveries")
