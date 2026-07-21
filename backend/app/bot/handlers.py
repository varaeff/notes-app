import logging

from telegram import Chat, Message, Update, User
from telegram.ext import ContextTypes

from app.db import SessionLocal
from app.services.telegram_settings import (
    TelegramChatAlreadyLinkedError,
    TelegramLinkCodeExpiredError,
    TelegramLinkCodeNotFoundError,
    connect_telegram_by_code,
)

from .messages import (
    TELEGRAM_CHAT_ALREADY_LINKED,
    TELEGRAM_CODE_EXPIRED,
    TELEGRAM_CODE_NOT_FOUND,
    TELEGRAM_CODE_PROMPT,
    TELEGRAM_CONNECT_FAILED,
    TELEGRAM_CONNECT_SUCCESS,
    TELEGRAM_INVALID_CODE,
)

logger = logging.getLogger(__name__)


def _telegram_username(telegram_user: User | None) -> str | None:
    if telegram_user is None:
        return None

    return telegram_user.username


async def _connect_from_code(
    message: Message,
    chat: Chat,
    telegram_user: User | None,
    code: str,
) -> None:
    if len(code) != 6 or not code.isdigit():
        await message.reply_text(TELEGRAM_INVALID_CODE)
        return

    db = SessionLocal()

    try:
        connect_telegram_by_code(
            db,
            code=code,
            chat_id=chat.id,
            username=_telegram_username(telegram_user),
        )
    except TelegramLinkCodeNotFoundError:
        await message.reply_text(TELEGRAM_CODE_NOT_FOUND)
    except TelegramLinkCodeExpiredError:
        await message.reply_text(TELEGRAM_CODE_EXPIRED)
    except TelegramChatAlreadyLinkedError:
        await message.reply_text(TELEGRAM_CHAT_ALREADY_LINKED)
    except Exception:
        db.rollback()
        logger.exception("Failed to connect Telegram account")
        await message.reply_text(TELEGRAM_CONNECT_FAILED)
    else:
        await message.reply_text(TELEGRAM_CONNECT_SUCCESS)
    finally:
        db.close()


async def start_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.effective_message
    chat = update.effective_chat

    if message is None:
        return

    args = context.args or []
    if args and chat is not None:
        await _connect_from_code(
            message,
            chat,
            update.effective_user,
            args[0].strip(),
        )
        return

    await message.reply_text(TELEGRAM_CODE_PROMPT)


async def link_code_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.effective_message
    chat = update.effective_chat

    if message is None or chat is None or message.text is None:
        return

    await _connect_from_code(
        message,
        chat,
        update.effective_user,
        message.text.strip(),
    )
