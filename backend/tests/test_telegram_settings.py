from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import hash_password
from app.config import settings
from app.db import Base
from app.models import TelegramSettings, User
from app.services.telegram_settings import complete_telegram_link


def _auth(client, username="telegram-user", password="pw123456"):
    client.post("/api/auth/register", json={"username": username, "password": password})
    response = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


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


def test_create_link_returns_telegram_url(client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "telegram_bot_username",
        "test_notes_bot",
    )

    response = client.post(
        "/api/settings/telegram/link",
        headers=_auth(client),
    )

    assert response.status_code == 200

    body = response.json()

    assert body["url"].startswith("https://t.me/test_notes_bot?start=")
    assert body["expires_at"] is not None


def test_complete_telegram_link():
    engine = create_engine("sqlite:///:memory:", future=True)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = testing_session()

    try:
        user = User(
            username="telegram-test-user",
            password_hash=hash_password("test-password"),
        )
        db.add(user)
        db.flush()

        token = "test-link-token-with-sufficient-length-123456"

        telegram_settings = TelegramSettings(
            user_id=user.id,
            notifications_enabled=False,
            timezone="UTC",
            link_token=token,
            link_token_expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
        db.add(telegram_settings)
        db.commit()

        result = complete_telegram_link(
            db,
            token=token,
            chat_id=123456789,
            username="test_user",
        )

        assert result.id == telegram_settings.id
        assert result.user_id == user.id
        assert result.chat_id == 123456789
        assert result.username == "test_user"
        assert result.notifications_enabled is False
        assert result.link_token is None
        assert result.link_token_expires_at is None

        db.refresh(telegram_settings)

        assert telegram_settings.chat_id == 123456789
        assert telegram_settings.username == "test_user"
        assert telegram_settings.link_token is None
        assert telegram_settings.link_token_expires_at is None
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
