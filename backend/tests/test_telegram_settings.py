import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import hash_password
from app.bot.handlers import link_code_handler, start_handler
from app.config import settings
from app.db import Base
from app.models import TelegramSettings, User
from app.services.telegram_settings import (
    TelegramChatAlreadyLinkedError,
    TelegramLinkCodeExpiredError,
    TelegramLinkCodeNotFoundError,
    connect_telegram_by_code,
    create_telegram_link_code,
)


class TelegramMessageStub:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


class TelegramChatStub:
    def __init__(self, chat_id: int) -> None:
        self.id = chat_id


class TelegramUserStub:
    def __init__(self, username: str | None) -> None:
        self.username = username


class TelegramUpdateStub:
    def __init__(
        self,
        *,
        message: TelegramMessageStub,
        chat: TelegramChatStub | None,
        user: TelegramUserStub | None,
    ) -> None:
        self.effective_message = message
        self.effective_chat = chat
        self.effective_user = user


class TelegramContextStub:
    def __init__(self, args: list[str] | None = None) -> None:
        self.args = args or []


def _auth(client, username="telegram-user", password="pw123456"):
    client.post("/api/auth/register", json={"username": username, "password": password})
    response = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_db():
    engine = create_engine("sqlite:///:memory:", future=True)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return engine, testing_session


def _create_user(db, username: str = "telegram-test-user") -> User:
    user = User(
        username=username,
        password_hash=hash_password("test-password"),
    )
    db.add(user)
    db.flush()
    return user


def _create_telegram_settings(
    db,
    user: User,
    *,
    code: str,
    chat_id: int | None = None,
    expires_at: datetime | None = None,
) -> TelegramSettings:
    telegram_settings = TelegramSettings(
        user_id=user.id,
        chat_id=chat_id,
        notifications_enabled=False,
        timezone="UTC",
        link_code=code,
        link_code_expires_at=expires_at or datetime.now(UTC) + timedelta(minutes=15),
    )
    db.add(telegram_settings)
    db.commit()
    return telegram_settings


def test_get_telegram_settings_returns_defaults(client):
    response = client.get(
        "/api/settings/telegram",
        headers=_auth(client),
    )

    assert response.status_code == 200
    assert response.json() == {
        "is_connected": False,
        "username": None,
        "notifications_enabled": False,
        "timezone": "UTC",
    }


def test_update_telegram_timezone(client):
    response = client.patch(
        "/api/settings/telegram",
        headers=_auth(client),
        json={"timezone": "Asia/Tbilisi"},
    )

    assert response.status_code == 200
    assert response.json()["timezone"] == "Asia/Tbilisi"


def test_cannot_enable_notifications_without_connection(client):
    response = client.patch(
        "/api/settings/telegram",
        headers=_auth(client),
        json={"notifications_enabled": True},
    )

    assert response.status_code == 409


def test_create_link_code_returns_six_digit_code(client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "telegram_bot_username",
        "test_notes_bot",
    )
    monkeypatch.setattr(
        "app.services.telegram_settings.secrets.randbelow",
        lambda upper_bound: 42,
    )

    response = client.post(
        "/api/settings/telegram/link-code",
        headers=_auth(client),
    )

    assert response.status_code == 200

    body = response.json()

    assert body == {
        "code": "000042",
        "expires_at": body["expires_at"],
        "bot_username": "test_notes_bot",
    }


def test_create_link_code_replaces_existing_pending_code(monkeypatch):
    engine, testing_session = _create_db()
    db = testing_session()

    try:
        monkeypatch.setattr(
            "app.services.telegram_settings.secrets.randbelow",
            lambda upper_bound: 1,
        )
        user = _create_user(db)
        first = create_telegram_link_code(db, user)
        assert first.link_code == "000001"

        monkeypatch.setattr(
            "app.services.telegram_settings.secrets.randbelow",
            lambda upper_bound: 2,
        )
        second = create_telegram_link_code(db, user)

        assert second.id == first.id
        assert second.link_code == "000002"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_connect_telegram_by_code():
    engine, testing_session = _create_db()
    db = testing_session()

    try:
        user = _create_user(db)
        telegram_settings = _create_telegram_settings(db, user, code="483921")

        result = connect_telegram_by_code(
            db,
            code="483921",
            chat_id=123456789,
            username="test_user",
        )

        assert result.id == telegram_settings.id
        assert result.user_id == user.id
        assert result.chat_id == 123456789
        assert result.username == "test_user"
        assert result.notifications_enabled is False
        assert result.link_code is None
        assert result.link_code_expires_at is None

        db.refresh(telegram_settings)

        assert telegram_settings.chat_id == 123456789
        assert telegram_settings.username == "test_user"
        assert telegram_settings.link_code is None
        assert telegram_settings.link_code_expires_at is None
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_connect_telegram_by_code_rejects_unknown_or_used_code():
    engine, testing_session = _create_db()
    db = testing_session()

    try:
        with pytest.raises(TelegramLinkCodeNotFoundError):
            connect_telegram_by_code(
                db,
                code="000000",
                chat_id=123456789,
                username="test_user",
            )
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_connect_telegram_by_code_rejects_expired_code():
    engine, testing_session = _create_db()
    db = testing_session()

    try:
        user = _create_user(db)
        telegram_settings = _create_telegram_settings(
            db,
            user,
            code="483921",
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )

        with pytest.raises(TelegramLinkCodeExpiredError):
            connect_telegram_by_code(
                db,
                code="483921",
                chat_id=123456789,
                username="test_user",
            )

        db.refresh(telegram_settings)

        assert telegram_settings.chat_id is None
        assert telegram_settings.link_code is None
        assert telegram_settings.link_code_expires_at is None
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_connect_telegram_by_code_rejects_chat_linked_to_another_user():
    engine, testing_session = _create_db()
    db = testing_session()

    try:
        first_user = _create_user(db, "first-user")
        second_user = _create_user(db, "second-user")
        _create_telegram_settings(db, first_user, code="111111", chat_id=123456789)
        _create_telegram_settings(db, second_user, code="222222")

        with pytest.raises(TelegramChatAlreadyLinkedError):
            connect_telegram_by_code(
                db,
                code="222222",
                chat_id=123456789,
                username="test_user",
            )
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_bot_link_code_handler_connects_telegram(monkeypatch):
    engine, testing_session = _create_db()
    db = testing_session()
    verify_db = None

    try:
        user = _create_user(db)
        _create_telegram_settings(db, user, code="483921")
        db.close()

        monkeypatch.setattr("app.bot.handlers.SessionLocal", testing_session)

        message = TelegramMessageStub("483921")
        update = TelegramUpdateStub(
            message=message,
            chat=TelegramChatStub(123456789),
            user=TelegramUserStub("test_user"),
        )

        asyncio.run(link_code_handler(update, TelegramContextStub()))

        assert message.replies == ["Telegram has been connected successfully."]

        verify_db = testing_session()
        connected_settings = verify_db.query(TelegramSettings).one()

        assert connected_settings.chat_id == 123456789
        assert connected_settings.username == "test_user"
        assert connected_settings.link_code is None
    finally:
        if verify_db is not None:
            verify_db.close()
        Base.metadata.drop_all(bind=engine)


def test_bot_start_handler_accepts_code_argument(monkeypatch):
    engine, testing_session = _create_db()
    db = testing_session()

    try:
        user = _create_user(db)
        _create_telegram_settings(db, user, code="483921")
        db.close()

        monkeypatch.setattr("app.bot.handlers.SessionLocal", testing_session)

        message = TelegramMessageStub("/start 483921")
        update = TelegramUpdateStub(
            message=message,
            chat=TelegramChatStub(123456789),
            user=TelegramUserStub("test_user"),
        )

        asyncio.run(start_handler(update, TelegramContextStub(["483921"])))

        assert message.replies == ["Telegram has been connected successfully."]
    finally:
        Base.metadata.drop_all(bind=engine)


def test_bot_link_code_handler_rejects_invalid_text():
    message = TelegramMessageStub("not-a-code")
    update = TelegramUpdateStub(
        message=message,
        chat=TelegramChatStub(123456789),
        user=TelegramUserStub("test_user"),
    )

    asyncio.run(link_code_handler(update, TelegramContextStub()))

    assert message.replies == ["Enter the six-digit connection code from the notes application."]
