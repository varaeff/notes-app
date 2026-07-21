from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User
from app.schemas import TelegramLinkCodeResponse, TelegramSettingsResponse, TelegramSettingsUpdate
from app.services.telegram_settings import (
    build_telegram_settings_response,
    create_telegram_link_code,
    get_or_create_telegram_settings,
)
from app.services.telegram_settings import (
    disconnect_telegram as disconnect_telegram_settings,
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

    if update_data.get("notifications_enabled") is True and telegram_settings.chat_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Telegram account is not connected",
        )

    for field, value in update_data.items():
        setattr(telegram_settings, field, value)

    db.commit()
    db.refresh(telegram_settings)

    return build_telegram_settings_response(telegram_settings)


@router.post("/link-code", response_model=TelegramLinkCodeResponse)
def create_telegram_link_code_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TelegramLinkCodeResponse:
    if not settings.telegram_bot_username:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram integration is not configured",
        )

    telegram_settings = create_telegram_link_code(db, current_user)

    if telegram_settings.link_code is None or telegram_settings.link_code_expires_at is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Telegram link code was not created",
        )

    return TelegramLinkCodeResponse(
        code=telegram_settings.link_code,
        expires_at=telegram_settings.link_code_expires_at,
        bot_username=settings.telegram_bot_username,
    )


@router.delete("/link", response_model=TelegramSettingsResponse)
def disconnect_telegram(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TelegramSettingsResponse:
    telegram_settings = disconnect_telegram_settings(db, current_user)

    return build_telegram_settings_response(telegram_settings)
