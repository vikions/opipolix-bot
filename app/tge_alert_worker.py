import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

from tge_alert_config import find_keywords, format_keywords, truncate_text
from tge_alert_db import TgeAlertDatabase
from tge_discord_monitor import DiscordMonitor
from tge_projects import get_project_config


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class TgeAlertWorker:
    def __init__(self, telegram_token: str, discord_token: Optional[str]):
        self.db = TgeAlertDatabase()
        self.bot = Bot(token=telegram_token)

        self.discord_monitor = None
        if discord_token:
            self.discord_monitor = DiscordMonitor(discord_token, min_interval_sec=60)
        else:
            logger.warning("Discord monitoring disabled")

        self.check_interval = 30
        self._running = True

        logger.info("TGE Alert worker initialized (interval=%ss)", self.check_interval)

    async def send_notification(self, telegram_id: int, message: str) -> None:
        try:
            await self.bot.send_message(chat_id=telegram_id, text=message)
            logger.info("Sent TGE alert to %s", telegram_id)
        except TelegramError:
            logger.exception("Failed to send TGE alert to %s", telegram_id)

    async def check_discord_alerts(self) -> None:
        if not self.discord_monitor:
            logger.debug("Discord monitoring disabled (missing token)")
            return

        alerts = self.db.get_active_alerts()
        if not alerts:
            logger.debug("No active TGE alerts for Discord")
            return

        projects = self._group_alerts_by_project(alerts)

        for project_name, data in projects.items():
            try:
                channel_id = data.get("discord_channel_id")
                if not channel_id:
                    logger.info("Discord channel not configured for %s", project_name)
                    continue

                messages = await self.discord_monitor.fetch_messages(channel_id, limit=10)
                if not messages:
                    continue

                last_seen = self.db.get_last_discord_message_id(project_name, channel_id)
                if not last_seen:
                    newest = self._max_message_id(messages)
                    if newest:
                        self.db.set_last_discord_message_id(project_name, channel_id, newest)
                    logger.info("Initialized Discord cursor for %s", project_name)
                    continue

                new_messages = self._filter_new_messages(messages, last_seen)
                if not new_messages:
                    continue

                config = get_project_config(project_name)
                channel_label = self._format_channel_label(channel_id, config)
                server_id = config.discord_server_id if config else None

                for msg in new_messages:
                    content = msg.get("content", "")
                    if not content:
                        continue

                    for alert in data.get("alerts", []):
                        matches = find_keywords(content, alert.get("keywords"))
                        if not matches:
                            continue

                        message = self._build_discord_alert_message(
                            project_name=project_name,
                            channel_label=channel_label,
                            author_name=msg.get("author_name", "unknown"),
                            timestamp=msg.get("timestamp", ""),
                            keywords=matches,
                            content=content,
                            link=self._format_discord_link(server_id, channel_id, msg.get("id")),
                        )
                        await self.send_notification(alert["telegram_id"], message)

                newest = self._max_message_id(messages)
                if newest:
                    self.db.set_last_discord_message_id(project_name, channel_id, newest)
            except Exception:
                logger.exception("Discord check failed for %s", project_name)

    async def run(self) -> None:
        logger.info("TGE Alert worker started")

        while self._running:
            try:
                await self.check_discord_alerts()
            except Exception:
                logger.exception("Unexpected error during TGE alert checks")

            await asyncio.sleep(self.check_interval)

        logger.info("TGE Alert worker stopped")

    async def shutdown(self) -> None:
        self._running = False
        if self.discord_monitor:
            await self.discord_monitor.close()

    def _group_alerts_by_project(self, alerts: List[Dict]) -> Dict[str, Dict]:
        projects: Dict[str, Dict] = {}
        for alert in alerts:
            project_name = alert.get("project_name")
            if not project_name:
                continue
            entry = projects.setdefault(
                project_name, {"alerts": [], "discord_channel_id": alert.get("discord_channel_id")}
            )
            if not entry.get("discord_channel_id") and alert.get("discord_channel_id"):
                entry["discord_channel_id"] = alert.get("discord_channel_id")
            entry["alerts"].append(alert)
        return projects

    def _filter_new_messages(self, messages: List[Dict], last_seen: str) -> List[Dict]:
        try:
            last_seen_id = int(last_seen)
        except (TypeError, ValueError):
            last_seen_id = 0

        new_items = []
        for msg in messages:
            try:
                msg_id = int(msg.get("id"))
            except (TypeError, ValueError):
                continue
            if msg_id > last_seen_id:
                new_items.append(msg)

        new_items.sort(key=lambda item: int(item["id"]))
        return new_items

    def _max_message_id(self, messages: List[Dict]) -> Optional[str]:
        ids = []
        for msg in messages:
            try:
                ids.append(int(msg.get("id")))
            except (TypeError, ValueError):
                continue
        if not ids:
            return None
        return str(max(ids))

    def _format_channel_label(self, channel_id: str, config) -> str:
        if config and config.discord_channel_name:
            return f"#{config.discord_channel_name}"
        return f"#{channel_id}"

    def _format_discord_link(
        self, server_id: Optional[str], channel_id: str, message_id: Optional[str]
    ) -> str:
        if not server_id or not message_id:
            return "N/A"
        return f"https://discord.com/channels/{server_id}/{channel_id}/{message_id}"

    def _format_time(self, timestamp: str) -> str:
        if not timestamp:
            return "unknown"
        try:
            cleaned = timestamp.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(cleaned)
            return parsed.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return timestamp

    def _build_discord_alert_message(
        self,
        project_name: str,
        channel_label: str,
        author_name: str,
        timestamp: str,
        keywords: List[str],
        content: str,
        link: str,
    ) -> str:
        return (
            f"🚨 TGE ALERT: {project_name}\n"
            f"📢 New message in {channel_label}\n"
            f"👤 Author: {author_name}\n"
            f"⏰ Time: {self._format_time(timestamp)}\n"
            f"🔑 Keywords found: {format_keywords(keywords)}\n"
            "💬 Message:\n"
            f"{truncate_text(content)}\n"
            f"🔗 Read full: {link}"
        )

async def main() -> None:
    load_dotenv()

    telegram_token = os.getenv("TELEGRAM_TOKEN")
    discord_token = os.getenv("DISCORD_TOKEN")
    if not telegram_token:
        raise SystemExit("TELEGRAM_TOKEN not found in environment.")

    worker = TgeAlertWorker(telegram_token, discord_token)

    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("TGE Alert worker stopped by user.")
    finally:
        await worker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
