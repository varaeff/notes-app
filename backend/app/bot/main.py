import logging

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from app.bot.handlers import link_code_handler, start_handler
from app.config import settings

logger = logging.getLogger(__name__)


def build_application() -> Application | None:
    if not settings.telegram_bot_token:
        logger.info("Telegram bot token is not configured; polling is disabled")
        return None

    application = Application.builder().token(settings.telegram_bot_token).build()
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            link_code_handler,
        )
    )
    return application


def run_polling() -> None:
    application = build_application()
    if application is None:
        return

    application.run_polling()


if __name__ == "__main__":
    run_polling()
