from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo


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
