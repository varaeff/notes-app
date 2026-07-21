import asyncio
from unittest.mock import AsyncMock

import pytest
from telegram.error import BadRequest, Forbidden, NetworkError, TelegramError

from app.bot.messages import TELEGRAM_TEST_MESSAGE
from app.config import settings
from app.services.telegram_notifications import (
    TelegramChatUnavailableError,
    TelegramDeliveryError,
    TelegramNotConfiguredError,
    TelegramNotConnectedError,
    send_telegram_message,
    send_test_telegram_message,
)


def test_send_test_message_rejects_missing_chat_id() -> None:
    with pytest.raises(TelegramNotConnectedError):
        asyncio.run(
            send_test_telegram_message(
                telegram_chat_id=None,
            )
        )


def test_send_test_message_rejects_missing_bot_token(monkeypatch) -> None:
    monkeypatch.setattr(settings, "telegram_bot_token", None)

    with pytest.raises(TelegramNotConfiguredError):
        asyncio.run(
            send_test_telegram_message(
                telegram_chat_id=123456789,
            )
        )


def test_send_test_message_uses_connected_chat_id(monkeypatch) -> None:
    send_message_mock = AsyncMock()
    monkeypatch.setattr(
        "app.services.telegram_notifications.send_telegram_message",
        send_message_mock,
    )

    asyncio.run(
        send_test_telegram_message(
            telegram_chat_id=123456789,
        )
    )

    send_message_mock.assert_awaited_once_with(
        chat_id=123456789,
        text=TELEGRAM_TEST_MESSAGE,
    )


def test_send_message_maps_forbidden_to_unavailable() -> None:
    client = AsyncMock()
    client.send_message.side_effect = Forbidden("blocked")

    with pytest.raises(TelegramChatUnavailableError):
        asyncio.run(
            send_telegram_message(
                chat_id=123456789,
                text=TELEGRAM_TEST_MESSAGE,
                client=client,
            )
        )


def test_send_message_maps_bad_request_to_unavailable() -> None:
    client = AsyncMock()
    client.send_message.side_effect = BadRequest("chat not found")

    with pytest.raises(TelegramChatUnavailableError):
        asyncio.run(
            send_telegram_message(
                chat_id=123456789,
                text=TELEGRAM_TEST_MESSAGE,
                client=client,
            )
        )


def test_send_message_maps_network_error_to_delivery_error() -> None:
    client = AsyncMock()
    client.send_message.side_effect = NetworkError("network")

    with pytest.raises(TelegramDeliveryError):
        asyncio.run(
            send_telegram_message(
                chat_id=123456789,
                text=TELEGRAM_TEST_MESSAGE,
                client=client,
            )
        )


def test_send_message_maps_unexpected_telegram_error_to_delivery_error() -> None:
    client = AsyncMock()
    client.send_message.side_effect = TelegramError("telegram")

    with pytest.raises(TelegramDeliveryError):
        asyncio.run(
            send_telegram_message(
                chat_id=123456789,
                text=TELEGRAM_TEST_MESSAGE,
                client=client,
            )
        )
