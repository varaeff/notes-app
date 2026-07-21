from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import TelegramSettings, User
from app.schemas import TelegramSettingsResponse


def get_or_create_telegram_settings(
    db: Session,
    user: User,
) -> TelegramSettings:
    telegram_settings = (
        db.query(TelegramSettings).filter(TelegramSettings.user_id == user.id).one_or_none()
    )

    if telegram_settings is not None:
        return telegram_settings

    telegram_settings = TelegramSettings(
        user_id=user.id,
        notifications_enabled=False,
        timezone="UTC",
    )

    db.add(telegram_settings)
    db.flush()

    return telegram_settings


def build_telegram_settings_response(
    telegram_settings: TelegramSettings,
) -> TelegramSettingsResponse:
    return TelegramSettingsResponse(
        is_connected=telegram_settings.chat_id is not None,
        username=telegram_settings.username,
        notifications_enabled=telegram_settings.notifications_enabled,
        timezone=telegram_settings.timezone,
    )


def complete_telegram_link(
    db: Session,
    *,
    token: str,
    chat_id: int,
    username: str | None,
) -> TelegramSettings:
    now = datetime.now(UTC)

    telegram_settings = (
        db.query(TelegramSettings).filter(TelegramSettings.link_token == token).one_or_none()
    )

    if telegram_settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Telegram link token not found",
        )

    expires_at = telegram_settings.link_token_expires_at
    if expires_at is not None and (expires_at.tzinfo is None or expires_at.utcoffset() is None):
        expires_at = expires_at.replace(tzinfo=UTC)

    if expires_at is None or expires_at <= now:
        telegram_settings.link_token = None
        telegram_settings.link_token_expires_at = None
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Telegram link token has expired",
        )

    existing_chat = (
        db.query(TelegramSettings)
        .filter(
            TelegramSettings.chat_id == chat_id,
            TelegramSettings.id != telegram_settings.id,
        )
        .one_or_none()
    )

    if existing_chat is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Telegram account is already linked to another user",
        )

    telegram_settings.chat_id = chat_id
    telegram_settings.username = username
    telegram_settings.link_token = None
    telegram_settings.link_token_expires_at = None

    db.commit()
    db.refresh(telegram_settings)

    return telegram_settings
