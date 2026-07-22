import asyncio
import contextlib
import logging
from collections.abc import Callable

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.services.reminders import (
    has_enabled_telegram_reminders,
    process_due_reminders,
)

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Session]


class ReminderWorkerManager:
    def __init__(
        self,
        *,
        session_factory: SessionFactory = SessionLocal,
        interval_seconds: float = 60,
    ) -> None:
        self._session_factory = session_factory
        self._interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def sync(self) -> None:
        if not settings.telegram_bot_token:
            await self.stop()
            logger.info("Reminder worker is disabled because Telegram bot token is not configured")
            return

        if self._has_enabled_reminders():
            await self.start()
        else:
            await self.stop()
            logger.info("Reminder worker is stopped because no Telegram reminders are enabled")

    async def start(self) -> None:
        async with self._lock:
            if self.is_running:
                return

            self._task = asyncio.create_task(self._run_loop())
            logger.info("Reminder worker started")

    async def stop(self) -> None:
        async with self._lock:
            task = self._task
            if task is None:
                return

            self._task = None
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

            logger.info("Reminder worker stopped")

    def _has_enabled_reminders(self) -> bool:
        db = self._session_factory()

        try:
            return has_enabled_telegram_reminders(db)
        except SQLAlchemyError:
            logger.exception("Failed to check Telegram reminder worker eligibility")
            return False
        finally:
            db.close()

    async def _run_loop(self) -> None:
        while True:
            db = self._session_factory()

            try:
                delivered_count = await process_due_reminders(db)
            except Exception:
                logger.exception("Reminder worker scan failed")
            else:
                if delivered_count:
                    logger.info("Reminder worker delivered %s reminders", delivered_count)
            finally:
                db.close()

            await asyncio.sleep(self._interval_seconds)


reminder_worker_manager = ReminderWorkerManager()
