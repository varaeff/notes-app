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

logger = logging.getLogger(__name__)

_CODE_PROMPT = "Send the six-digit connection code shown in the notes application."
_INVALID_CODE = "Enter the six-digit connection code from the notes application."
_CODE_NOT_FOUND = "The connection code is invalid or has already been used."
_CODE_EXPIRED = "The connection code has expired. Generate a new code in the notes application."
_CHAT_ALREADY_LINKED = "This Telegram account is already connected to another application user."
_CONNECT_FAILED = "Could not connect Telegram. Try again later."
_CONNECT_SUCCESS = "Telegram has been connected successfully."


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
        await message.reply_text(_INVALID_CODE)
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
        await message.reply_text(_CODE_NOT_FOUND)
    except TelegramLinkCodeExpiredError:
        await message.reply_text(_CODE_EXPIRED)
    except TelegramChatAlreadyLinkedError:
        await message.reply_text(_CHAT_ALREADY_LINKED)
    except Exception:
        db.rollback()
        logger.exception("Failed to connect Telegram account")
        await message.reply_text(_CONNECT_FAILED)
    else:
        await message.reply_text(_CONNECT_SUCCESS)
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

    await message.reply_text(_CODE_PROMPT)


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
