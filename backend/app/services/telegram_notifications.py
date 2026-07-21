import logging

from telegram import Bot
from telegram.error import BadRequest, Forbidden, NetworkError, TelegramError

from app.bot.messages import TELEGRAM_TEST_MESSAGE
from app.config import settings

logger = logging.getLogger(__name__)


class TelegramNotConfiguredError(Exception):
    pass


class TelegramNotConnectedError(Exception):
    pass


class TelegramDeliveryError(Exception):
    pass


class TelegramChatUnavailableError(TelegramDeliveryError):
    pass


class TelegramClient:
    def __init__(self, token: str) -> None:
        self._token = token

    async def send_message(
        self,
        *,
        chat_id: int,
        text: str,
    ) -> None:
        bot = Bot(token=self._token)

        async with bot:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
            )


async def send_telegram_message(
    *,
    chat_id: int,
    text: str,
    client: TelegramClient | None = None,
) -> None:
    if client is None:
        if not settings.telegram_bot_token:
            raise TelegramNotConfiguredError

        client = TelegramClient(settings.telegram_bot_token)

    try:
        await client.send_message(
            chat_id=chat_id,
            text=text,
        )
    except Forbidden as exc:
        logger.warning(
            "Telegram bot cannot access chat %s: %s",
            chat_id,
            exc,
        )
        raise TelegramChatUnavailableError from exc

    except BadRequest as exc:
        logger.warning(
            "Telegram rejected message for chat %s: %s",
            chat_id,
            exc,
        )
        raise TelegramChatUnavailableError from exc

    except NetworkError as exc:
        logger.exception(
            "Telegram network error for chat %s",
            chat_id,
        )
        raise TelegramDeliveryError from exc

    except TelegramError as exc:
        logger.exception(
            "Unexpected Telegram error for chat %s",
            chat_id,
        )
        raise TelegramDeliveryError from exc

    logger.info("Telegram message delivered to chat %s", chat_id)


async def send_test_telegram_message(
    *,
    telegram_chat_id: int | None,
) -> None:
    if telegram_chat_id is None:
        raise TelegramNotConnectedError

    await send_telegram_message(
        chat_id=telegram_chat_id,
        text=TELEGRAM_TEST_MESSAGE,
    )
