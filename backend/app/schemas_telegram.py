import re
from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator


class TelegramSettingsResponse(BaseModel):
    is_connected: bool
    username: str | None
    notifications_enabled: bool
    timezone: str
    reminder_time: str


class TelegramSettingsUpdate(BaseModel):
    notifications_enabled: bool | None = None
    timezone: str | None = Field(default=None, max_length=64)
    reminder_time: time | None = None

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None

        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("Invalid IANA timezone") from error

        return value

    @field_validator("reminder_time", mode="before")
    @classmethod
    def validate_reminder_time(cls, value: str | time | None) -> str | time | None:
        if value is None or isinstance(value, time):
            return value

        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", value):
            raise ValueError("Invalid reminder time")

        return value


class TelegramLinkCodeResponse(BaseModel):
    code: str
    expires_at: datetime
    bot_username: str


class TelegramTestMessageResponse(BaseModel):
    success: bool
    message: str
