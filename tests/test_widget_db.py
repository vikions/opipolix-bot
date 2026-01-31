import os
import sqlite3
import tempfile
import unittest

from app.widget_db import WidgetDatabase


class TempDatabase:
    def __init__(self, path: str):
        self.use_postgres = False
        self.path = path

    def get_connection(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn


class WidgetDbTest(unittest.TestCase):
    def setUp(self):
        self.tmp_file = tempfile.NamedTemporaryFile(delete=False)
        self.tmp_file.close()
        self.db = TempDatabase(self.tmp_file.name)
        self.widget_db = WidgetDatabase(self.db)

    def tearDown(self):
        if os.path.exists(self.tmp_file.name):
            os.unlink(self.tmp_file.name)

    def test_widget_crud(self):
        widget_id = self.widget_db.create_widget(
            owner_user_id=123,
            target_chat_id=999,
            board_message_id=555,
            selected_market_ids=["opinion", "opensea"],
            interval_seconds=60,
            enabled=True,
        )

        widget = self.widget_db.get_widget_by_id(widget_id)
        self.assertIsNotNone(widget)
        self.assertEqual(widget["owner_user_id"], 123)
        self.assertEqual(widget["selected_market_ids"], ["opinion", "opensea"])
        self.assertTrue(widget["enabled"])
        self.assertTrue(widget.get("compact_mode", True))

        self.widget_db.update_widget_markets(widget_id, ["metamask"])
        widget = self.widget_db.get_widget_by_id(widget_id)
        self.assertEqual(widget["selected_market_ids"], ["metamask"])

        self.widget_db.update_widget_interval(widget_id, 120)
        widget = self.widget_db.get_widget_by_id(widget_id)
        self.assertEqual(widget["interval_seconds"], 120)

        self.widget_db.set_widget_enabled(widget_id, False)
        widget = self.widget_db.get_widget_by_id(widget_id)
        self.assertFalse(widget["enabled"])

        self.widget_db.delete_widget(widget_id)
        widget = self.widget_db.get_widget_by_id(widget_id)
        self.assertIsNone(widget)


if __name__ == "__main__":
    unittest.main()
