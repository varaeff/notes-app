import asyncio
from datetime import UTC, date, datetime, time
from unittest.mock import AsyncMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import hash_password
from app.db import Base
from app.models import Note, User
from app.models_telegram import (
    NoteReminderDelivery,
    ReminderDeliveryStatus,
    TelegramSettings,
)
from app.services.reminders import (
    build_reminder_message,
    has_enabled_telegram_reminders,
    process_due_reminders,
)
from app.services.telegram_notifications import TelegramDeliveryError
from app.workers.reminder_worker import ReminderWorkerManager


def _create_db():
    engine = create_engine("sqlite:///:memory:", future=True)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return engine, testing_session


def _create_user(db, username: str = "reminder-user") -> User:
    user = User(
        username=username,
        password_hash=hash_password("test-password"),
    )
    db.add(user)
    db.flush()
    return user


def _create_note(
    db,
    user: User,
    *,
    title: str = "Doctor appointment",
    note_date: date | None = date(2026, 4, 10),
) -> Note:
    note = Note(
        user_id=user.id,
        title=title,
        content="",
        tags=[],
        note_date=note_date,
    )
    db.add(note)
    db.flush()
    return note


def _create_telegram_settings(
    db,
    user: User,
    *,
    chat_id: int | None = 123456789,
    notifications_enabled: bool = True,
    reminder_time: time = time(9, 0),
) -> TelegramSettings:
    telegram_settings = TelegramSettings(
        user_id=user.id,
        chat_id=chat_id,
        username="telegram_user",
        notifications_enabled=notifications_enabled,
        timezone="UTC",
        reminder_time=reminder_time,
    )
    db.add(telegram_settings)
    db.flush()
    return telegram_settings


def test_build_reminder_message_uses_note_title_and_date():
    engine, testing_session = _create_db()
    db = testing_session()

    try:
        user = _create_user(db)
        note = _create_note(db, user, title="Demo day")

        assert build_reminder_message(note) == 'Событие "Demo day" наступило 2026-04-10.'
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_process_due_reminders_delivers_due_note_once(monkeypatch):
    engine, testing_session = _create_db()
    db = testing_session()
    send_mock = AsyncMock()

    try:
        user = _create_user(db)
        note = _create_note(db, user)
        _create_telegram_settings(db, user)
        db.commit()

        monkeypatch.setattr("app.services.reminders.send_telegram_message", send_mock)

        first_count = asyncio.run(
            process_due_reminders(
                db,
                now=datetime(2026, 4, 10, 9, 1, tzinfo=UTC),
            )
        )
        second_count = asyncio.run(
            process_due_reminders(
                db,
                now=datetime(2026, 4, 10, 9, 2, tzinfo=UTC),
            )
        )

        delivery = db.query(NoteReminderDelivery).one()

        assert first_count == 1
        assert second_count == 0
        assert delivery.note_id == note.id
        assert delivery.status == ReminderDeliveryStatus.sent
        assert delivery.sent_at is not None
        send_mock.assert_awaited_once_with(
            chat_id=123456789,
            text='Событие "Doctor appointment" наступило 2026-04-10.',
        )
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_process_due_reminders_skips_disabled_unlinked_archived_and_future_notes(monkeypatch):
    engine, testing_session = _create_db()
    db = testing_session()
    send_mock = AsyncMock()

    try:
        disabled_user = _create_user(db, "disabled-user")
        _create_note(db, disabled_user)
        _create_telegram_settings(db, disabled_user, notifications_enabled=False)

        unlinked_user = _create_user(db, "unlinked-user")
        _create_note(db, unlinked_user)
        _create_telegram_settings(db, unlinked_user, chat_id=None)

        archived_user = _create_user(db, "archived-user")
        archived_note = _create_note(db, archived_user)
        archived_note.archived_at = datetime(2026, 4, 9, 12, 0, tzinfo=UTC)
        _create_telegram_settings(db, archived_user, chat_id=123456790)

        future_user = _create_user(db, "future-user")
        _create_note(db, future_user, note_date=date(2026, 4, 11))
        _create_telegram_settings(db, future_user, chat_id=123456791)

        db.commit()

        monkeypatch.setattr("app.services.reminders.send_telegram_message", send_mock)

        delivered_count = asyncio.run(
            process_due_reminders(
                db,
                now=datetime(2026, 4, 10, 9, 1, tzinfo=UTC),
            )
        )

        assert delivered_count == 0
        assert db.query(NoteReminderDelivery).count() == 0
        send_mock.assert_not_awaited()
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_process_due_reminders_records_retry_after_delivery_failure(monkeypatch):
    engine, testing_session = _create_db()
    db = testing_session()
    send_mock = AsyncMock(side_effect=TelegramDeliveryError)

    try:
        user = _create_user(db)
        _create_note(db, user)
        _create_telegram_settings(db, user)
        db.commit()

        monkeypatch.setattr("app.services.reminders.send_telegram_message", send_mock)

        delivered_count = asyncio.run(
            process_due_reminders(
                db,
                now=datetime(2026, 4, 10, 9, 1, tzinfo=UTC),
            )
        )
        retry_count = asyncio.run(
            process_due_reminders(
                db,
                now=datetime(2026, 4, 10, 9, 1, 30, tzinfo=UTC),
            )
        )

        delivery = db.query(NoteReminderDelivery).one()

        assert delivered_count == 0
        assert retry_count == 0
        assert delivery.status == ReminderDeliveryStatus.failed
        assert delivery.attempts == 1
        assert delivery.next_attempt_at is not None
        assert delivery.last_error == "TelegramDeliveryError"
        assert send_mock.await_count == 1
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_has_enabled_telegram_reminders_requires_linked_enabled_user():
    engine, testing_session = _create_db()
    db = testing_session()

    try:
        user = _create_user(db)
        _create_telegram_settings(db, user, chat_id=None, notifications_enabled=True)
        db.commit()

        assert has_enabled_telegram_reminders(db) is False

        telegram_settings = db.query(TelegramSettings).one()
        telegram_settings.chat_id = 123456789
        db.commit()

        assert has_enabled_telegram_reminders(db) is True
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_reminder_worker_manager_does_not_start_without_bot_token(monkeypatch):
    engine, testing_session = _create_db()
    db = testing_session()

    try:
        user = _create_user(db)
        _create_telegram_settings(db, user)
        db.commit()

        monkeypatch.setattr("app.workers.reminder_worker.settings.telegram_bot_token", None)

        manager = ReminderWorkerManager(
            session_factory=testing_session,
            interval_seconds=60,
        )

        asyncio.run(manager.sync())

        assert manager.is_running is False
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_reminder_worker_manager_starts_and_stops_from_enabled_state(monkeypatch):
    engine, testing_session = _create_db()
    db = testing_session()
    manager = None

    try:
        user = _create_user(db)
        _create_telegram_settings(db, user)
        db.commit()

        monkeypatch.setattr(
            "app.workers.reminder_worker.settings.telegram_bot_token",
            "test-token",
        )
        monkeypatch.setattr(
            "app.workers.reminder_worker.process_due_reminders",
            AsyncMock(return_value=0),
        )

        manager = ReminderWorkerManager(
            session_factory=testing_session,
            interval_seconds=60,
        )

        async def run_worker_lifecycle_check() -> None:
            await manager.sync()
            assert manager.is_running is True

            telegram_settings = db.query(TelegramSettings).one()
            telegram_settings.notifications_enabled = False
            db.commit()

            await manager.sync()
            assert manager.is_running is False

        asyncio.run(run_worker_lifecycle_check())
    finally:
        if manager is not None and manager.is_running:
            asyncio.run(manager.stop())
        db.close()
        Base.metadata.drop_all(bind=engine)
