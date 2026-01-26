import asyncio
import logging
import time
from typing import Dict, List, Optional

import discum


logger = logging.getLogger(__name__)


class DiscordMonitor:
    def __init__(self, token: str, min_interval_sec: int = 60):
        self.client = discum.Client(token=token, log=False)
        self.min_interval_sec = max(min_interval_sec, 60)
        self._last_call: Dict[str, float] = {}

    async def fetch_messages(self, channel_id: str, limit: int = 5) -> List[Dict]:
        if not channel_id:
            return []

        now = time.monotonic()
        last_call = self._last_call.get(channel_id)
        if last_call is not None and (now - last_call) < self.min_interval_sec:
            logger.debug("Discord rate limit active for channel %s", channel_id)
            return []

        self._last_call[channel_id] = now
        try:
            response = await asyncio.to_thread(
                self.client.getMessages, channel_id, num=limit
            )
        except Exception:
            logger.exception("Discord getMessages failed for channel %s", channel_id)
            return []

        try:
            if isinstance(response, list):
                payload = response
            elif hasattr(response, "json"):
                payload = response.json()
            else:
                payload = []
        except Exception:
            logger.exception("Discord response parsing failed for channel %s", channel_id)
            payload = []

        if not isinstance(payload, list):
            return []

        return [self._normalize_message(item) for item in payload if isinstance(item, dict)]

    def _normalize_message(self, message: Dict) -> Dict:
        author = message.get("author") or {}
        author_name = (
            author.get("global_name")
            or author.get("username")
            or author.get("id")
            or "unknown"
        )
        return {
            "id": message.get("id"),
            "content": message.get("content") or "",
            "author_name": author_name,
            "timestamp": message.get("timestamp") or "",
            "channel_id": message.get("channel_id"),
        }

    async def close(self) -> None:
        if hasattr(self.client, "close"):
            await asyncio.to_thread(self.client.close)
