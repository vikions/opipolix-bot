import unittest
from datetime import datetime, timedelta

from app.widget_updater import decide_widget_update, HEARTBEAT_SECONDS


class WidgetHeartbeatTest(unittest.TestCase):
    def test_heartbeat_triggers_after_interval(self):
        now = datetime(2026, 1, 31, 10, 0)
        last_heartbeat = now - timedelta(seconds=HEARTBEAT_SECONDS + 1)
        decision = decide_widget_update(
            now=now,
            last_render_hash="hash",
            last_heartbeat_at=last_heartbeat,
            market_hash="hash",
            heartbeat_seconds=HEARTBEAT_SECONDS,
        )
        self.assertEqual(decision, "heartbeat")

    def test_skip_when_no_change_and_recent_heartbeat(self):
        now = datetime(2026, 1, 31, 10, 0)
        last_heartbeat = now - timedelta(seconds=HEARTBEAT_SECONDS - 60)
        decision = decide_widget_update(
            now=now,
            last_render_hash="hash",
            last_heartbeat_at=last_heartbeat,
            market_hash="hash",
            heartbeat_seconds=HEARTBEAT_SECONDS,
        )
        self.assertEqual(decision, "skip")

    def test_data_change_overrides_heartbeat(self):
        now = datetime(2026, 1, 31, 10, 0)
        last_heartbeat = now - timedelta(seconds=HEARTBEAT_SECONDS - 60)
        decision = decide_widget_update(
            now=now,
            last_render_hash="old",
            last_heartbeat_at=last_heartbeat,
            market_hash="new",
            heartbeat_seconds=HEARTBEAT_SECONDS,
        )
        self.assertEqual(decision, "data_changed")


if __name__ == "__main__":
    unittest.main()
