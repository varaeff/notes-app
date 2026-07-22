import logging
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Note
from app.models_telegram import (
    NoteReminderDelivery,
    ReminderDeliveryStatus,
    TelegramSettings,
)
from app.services.telegram_notifications import (
    TelegramDeliveryError,
    TelegramNotConfiguredError,
    send_telegram_message,
)

logger = logging.getLogger(__name__)

MAX_DELIVERY_ERROR_LENGTH = 500


def build_reminder_scheduled_for(
    note_date: date,
    reminder_time: time,
    timezone: str,
) -> datetime:
    local_datetime = datetime.combine(
        note_date,
        reminder_time,
        tzinfo=ZoneInfo(timezone),
    )
    return local_datetime.astimezone(UTC)


def build_reminder_message(note: Note) -> str:
    return f'Событие "{note.title}" наступило {note.note_date.isoformat()}.'


def has_enabled_telegram_reminders(db: Session) -> bool:
    return (
        db.query(TelegramSettings.id)
        .filter(
            TelegramSettings.chat_id.is_not(None),
            TelegramSettings.notifications_enabled.is_(True),
        )
        .first()
        is not None
    )


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def _build_next_attempt_at(now: datetime, attempts: int) -> datetime:
    delay_minutes = min(2 ** max(attempts - 1, 0), 60)
    return now + timedelta(minutes=delay_minutes)


def _delivery_error_message(error: Exception) -> str:
    message = str(error) or error.__class__.__name__
    return message[:MAX_DELIVERY_ERROR_LENGTH]


def _is_delivery_retry_due(
    delivery: NoteReminderDelivery,
    now: datetime,
) -> bool:
    if delivery.status in {
        ReminderDeliveryStatus.sent,
        ReminderDeliveryStatus.processing,
        ReminderDeliveryStatus.cancelled,
    }:
        return False

    if delivery.next_attempt_at is None:
        return True

    return _normalize_utc(delivery.next_attempt_at) <= now


def _reserve_delivery(
    db: Session,
    *,
    note: Note,
    scheduled_for: datetime,
    now: datetime,
) -> NoteReminderDelivery | None:
    delivery = (
        db.query(NoteReminderDelivery)
        .filter(
            NoteReminderDelivery.note_id == note.id,
            NoteReminderDelivery.scheduled_for == scheduled_for,
        )
        .one_or_none()
    )

    if delivery is not None:
        if not _is_delivery_retry_due(delivery, now):
            return None

        delivery.status = ReminderDeliveryStatus.processing
        delivery.last_error = None
        db.commit()
        db.refresh(delivery)
        return delivery

    delivery = NoteReminderDelivery(
        note_id=note.id,
        user_id=note.user_id,
        scheduled_for=scheduled_for,
        status=ReminderDeliveryStatus.processing,
    )
    db.add(delivery)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return None

    db.refresh(delivery)
    return delivery


def _mark_delivery_sent(
    db: Session,
    delivery: NoteReminderDelivery,
    now: datetime,
) -> None:
    delivery.status = ReminderDeliveryStatus.sent
    delivery.sent_at = now
    delivery.next_attempt_at = None
    delivery.last_error = None
    db.commit()


def _mark_delivery_failed(
    db: Session,
    delivery: NoteReminderDelivery,
    now: datetime,
    error: Exception,
) -> None:
    delivery.attempts += 1
    delivery.status = ReminderDeliveryStatus.failed
    delivery.next_attempt_at = _build_next_attempt_at(now, delivery.attempts)
    delivery.last_error = _delivery_error_message(error)
    db.commit()


async def process_due_reminders(
    db: Session,
    *,
    now: datetime | None = None,
) -> int:
    current_time = _normalize_utc(now or datetime.now(UTC))
    delivered_count = 0

    candidates = (
        db.query(Note, TelegramSettings)
        .join(TelegramSettings, TelegramSettings.user_id == Note.user_id)
        .filter(
            Note.note_date.is_not(None),
            Note.archived_at.is_(None),
            TelegramSettings.chat_id.is_not(None),
            TelegramSettings.notifications_enabled.is_(True),
        )
        .all()
    )

    for note, telegram_settings in candidates:
        if note.note_date is None or telegram_settings.chat_id is None:
            continue

        scheduled_for = build_reminder_scheduled_for(
            note_date=note.note_date,
            reminder_time=telegram_settings.reminder_time,
            timezone=telegram_settings.timezone,
        )

        if scheduled_for > current_time:
            continue

        delivery = _reserve_delivery(
            db,
            note=note,
            scheduled_for=scheduled_for,
            now=current_time,
        )

        if delivery is None:
            continue

        try:
            await send_telegram_message(
                chat_id=telegram_settings.chat_id,
                text=build_reminder_message(note),
            )
        except (TelegramDeliveryError, TelegramNotConfiguredError) as error:
            logger.warning(
                "Failed to deliver reminder for note %s to Telegram chat %s",
                note.id,
                telegram_settings.chat_id,
            )
            _mark_delivery_failed(db, delivery, current_time, error)
            continue

        _mark_delivery_sent(db, delivery, current_time)
        delivered_count += 1

    return delivered_count
