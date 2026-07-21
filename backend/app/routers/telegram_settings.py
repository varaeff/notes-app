import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User
from app.schemas import TelegramLinkResponse, TelegramSettingsResponse, TelegramSettingsUpdate
from app.services.telegram_settings import (
    build_telegram_settings_response,
    get_or_create_telegram_settings,
)

from ..deps import get_current_user, get_db

router = APIRouter(
    prefix="/settings/telegram",
    tags=["telegram-settings"],
)


@router.get("", response_model=TelegramSettingsResponse)
def get_telegram_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TelegramSettingsResponse:
    telegram_settings = get_or_create_telegram_settings(db, current_user)

    db.commit()
    db.refresh(telegram_settings)

    return build_telegram_settings_response(telegram_settings)


@router.patch("", response_model=TelegramSettingsResponse)
def update_telegram_settings(
    payload: TelegramSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TelegramSettingsResponse:
    telegram_settings = get_or_create_telegram_settings(db, current_user)

    update_data = payload.model_dump(exclude_unset=True)

    if (
        update_data.get("notifications_enabled") is True
        and telegram_settings.chat_id is None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Telegram account is not connected",
        )

    for field, value in update_data.items():
        setattr(telegram_settings, field, value)

    db.commit()
    db.refresh(telegram_settings)

    return build_telegram_settings_response(telegram_settings)


@router.post("/link", response_model=TelegramLinkResponse)
def create_telegram_link(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TelegramLinkResponse:
    if not settings.telegram_bot_username:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram integration is not configured",
        )

    telegram_settings = get_or_create_telegram_settings(db, current_user)

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.telegram_link_token_ttl_minutes
    )

    telegram_settings.link_token = token
    telegram_settings.link_token_expires_at = expires_at

    db.commit()

    url = (
        f"https://t.me/{settings.telegram_bot_username}"
        f"?start={token}"
    )

    return TelegramLinkResponse(
        url=url,
        expires_at=expires_at,
    )


@router.delete("/link", response_model=TelegramSettingsResponse)
def disconnect_telegram(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TelegramSettingsResponse:
    telegram_settings = get_or_create_telegram_settings(db, current_user)

    telegram_settings.chat_id = None
    telegram_settings.username = None
    telegram_settings.notifications_enabled = False
    telegram_settings.link_token = None
    telegram_settings.link_token_expires_at = None

    db.commit()
    db.refresh(telegram_settings)

    return build_telegram_settings_response(telegram_settings)
