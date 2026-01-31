import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Optional

from telegram import Bot
from telegram.error import TelegramError

from widget_db import WidgetDatabase
from widget_updater import update_widget_message


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


PERMISSION_HELP_TEXT = (
    "📌 Widget update failed due to missing permissions.\n\n"
    "Please add @OpiPolixBot as an admin in the target chat with ONLY:\n"
    "• Pin messages\n"
    "• Edit messages\n\n"
    "After fixing permissions, use /widget to resume or refresh."
)


class WidgetWorker:
    def __init__(self, telegram_token: str):
        self.db = WidgetDatabase()
        self.bot = Bot(token=telegram_token)
        self.poll_interval = 10
        self._running = True
        logger.info("Widget worker initialized (interval=%ss)", self.poll_interval)

    def _is_due(self, widget: Dict[str, object]) -> bool:
        last_rendered_at = widget.get("last_rendered_at")
        interval_seconds = int(widget.get("interval_seconds") or 60)
        if not last_rendered_at:
            return True
        delta = (datetime.utcnow() - last_rendered_at).total_seconds()
        return delta >= interval_seconds

    async def _notify_permission_error(self, widget: Dict[str, object], error: str) -> None:
        owner_id = widget.get("owner_user_id")
        chat_title = widget.get("chat_title") or str(widget.get("target_chat_id"))
        message = (
            f"{PERMISSION_HELP_TEXT}\n\n"
            f"Chat: {chat_title}\n"
            f"Widget ID: {widget.get('widget_id')}\n"
            f"Error: {error}"
        )
        if not owner_id:
            return
        try:
            await self.bot.send_message(chat_id=owner_id, text=message)
        except TelegramError:
            logger.exception("Failed to DM widget owner %s", owner_id)

    async def _process_widget(self, widget: Dict[str, object]) -> None:
        result = await update_widget_message(self.bot, widget, self.db, force=False)
        status = result.get("status")

        if status == "updated":
            logger.info("Widget %s updated", widget.get("widget_id"))
            return

        if status == "retry_after":
            retry_after = float(result.get("retry_after") or 1)
            logger.warning("Rate limited, backing off for %ss", retry_after)
            await asyncio.sleep(retry_after)
            return

        if status == "permission_error":
            error = str(result.get("error") or "permission_error")
            logger.warning("Widget %s permission error: %s", widget.get("widget_id"), error)
            self.db.set_widget_enabled(int(widget.get("widget_id")), False)
            await self._notify_permission_error(widget, error)
            return

        if status == "error":
            logger.warning("Widget %s update failed: %s", widget.get("widget_id"), result.get("error"))

    async def run(self) -> None:
        logger.info("Widget worker started")

        while self._running:
            try:
                widgets = self.db.get_enabled_widgets()
                if widgets:
                    logger.info("Widget worker tick: %s widgets", len(widgets))
                for widget in widgets:
                    if not self._is_due(widget):
                        continue
                    await self._process_widget(widget)
            except Exception:
                logger.exception("Unexpected error during widget updates")

            await asyncio.sleep(self.poll_interval)

        logger.info("Widget worker stopped")

    async def shutdown(self) -> None:
        self._running = False


async def main() -> None:
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    if not telegram_token:
        raise SystemExit("TELEGRAM_TOKEN not found in environment.")

    worker = WidgetWorker(telegram_token)
    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Widget worker stopped by user.")
    finally:
        await worker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
