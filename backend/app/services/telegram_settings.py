import secrets
from datetime import UTC, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User
from app.models_telegram import TelegramSettings
from app.schemas_telegram import TelegramSettingsResponse


class TelegramLinkError(Exception):
    pass


class TelegramLinkCodeNotFoundError(TelegramLinkError):
    pass


class TelegramLinkCodeExpiredError(TelegramLinkError):
    pass


class TelegramChatAlreadyLinkedError(TelegramLinkError):
    pass


def get_or_create_telegram_settings(
    db: Session,
    user: User,
) -> TelegramSettings:
    telegram_settings = (
        db.query(TelegramSettings).filter(TelegramSettings.user_id == user.id).one_or_none()
    )

    if telegram_settings is not None:
        return telegram_settings

    try:
        telegram_settings = TelegramSettings(
            user_id=user.id,
            notifications_enabled=False,
            timezone="UTC",
            reminder_time=time(9, 0),
        )

        db.add(telegram_settings)
        db.flush()

        return telegram_settings
    except IntegrityError:
        db.rollback()
        return db.query(TelegramSettings).filter(TelegramSettings.user_id == user.id).one()


def build_telegram_settings_response(
    telegram_settings: TelegramSettings,
) -> TelegramSettingsResponse:
    return TelegramSettingsResponse(
        is_configured=bool(settings.telegram_bot_token and settings.telegram_bot_username),
        is_connected=telegram_settings.chat_id is not None,
        username=telegram_settings.username,
        notifications_enabled=telegram_settings.notifications_enabled,
        timezone=telegram_settings.timezone,
        reminder_time=telegram_settings.reminder_time.strftime("%H:%M"),
    )


def generate_telegram_link_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_unique_telegram_link_code(db: Session) -> str:
    for _ in range(10):
        code = generate_telegram_link_code()
        existing = db.scalar(select(TelegramSettings.id).where(TelegramSettings.link_code == code))

        if existing is None:
            return code

    raise RuntimeError("Could not generate a unique Telegram link code")


def create_telegram_link_code(
    db: Session,
    user: User,
) -> TelegramSettings:
    for _ in range(10):
        telegram_settings = get_or_create_telegram_settings(db, user)
        telegram_settings.link_code = generate_unique_telegram_link_code(db)
        telegram_settings.link_code_expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.telegram_link_code_ttl_minutes
        )

        try:
            db.commit()
            db.refresh(telegram_settings)
            return telegram_settings
        except IntegrityError:
            db.rollback()

    raise RuntimeError("Could not create a unique Telegram link code")


def _normalize_utc(value: datetime | None) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        return value.replace(tzinfo=UTC)

    return value


def connect_telegram_by_code(
    db: Session,
    *,
    code: str,
    chat_id: int,
    username: str | None,
) -> TelegramSettings:
    now = datetime.now(UTC)

    telegram_settings = (
        db.query(TelegramSettings).filter(TelegramSettings.link_code == code).one_or_none()
    )

    if telegram_settings is None:
        raise TelegramLinkCodeNotFoundError

    expires_at = _normalize_utc(telegram_settings.link_code_expires_at)

    if expires_at is None or expires_at <= now:
        telegram_settings.link_code = None
        telegram_settings.link_code_expires_at = None
        db.commit()

        raise TelegramLinkCodeExpiredError

    existing_chat = (
        db.query(TelegramSettings)
        .filter(
            TelegramSettings.chat_id == chat_id,
            TelegramSettings.id != telegram_settings.id,
        )
        .one_or_none()
    )

    if existing_chat is not None:
        raise TelegramChatAlreadyLinkedError

    try:
        telegram_settings.chat_id = chat_id
        telegram_settings.username = username
        telegram_settings.link_code = None
        telegram_settings.link_code_expires_at = None

        db.commit()
        db.refresh(telegram_settings)

        return telegram_settings
    except Exception:
        db.rollback()
        raise


def disconnect_telegram(
    db: Session,
    user: User,
) -> TelegramSettings:
    telegram_settings = get_or_create_telegram_settings(db, user)

    telegram_settings.chat_id = None
    telegram_settings.username = None
    telegram_settings.notifications_enabled = False
    telegram_settings.link_code = None
    telegram_settings.link_code_expires_at = None

    db.commit()
    db.refresh(telegram_settings)

    return telegram_settings
