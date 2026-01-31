import unittest
from datetime import datetime

from app.widget_renderer import (
    generate_market_aliases,
    render_widget_text,
)


class WidgetRendererTest(unittest.TestCase):
    def test_compact_rendering(self):
        snapshots = [
            {"name": "Opinion Token by February 17, 2026", "yes_value": 0.69, "no_value": 0.31},
            {"name": "OpenSea Token by March 31, 2026", "yes_value": 0.635, "no_value": 0.365},
        ]
        text = render_widget_text(snapshots, datetime(2026, 1, 31, 8, 14))
        lines = text.split("\n")

        self.assertIn("OpenS", text)
        self.assertIn("Opin", text)
        self.assertEqual(lines[-1], "UTC 08:14")
        self.assertNotIn("🟢", text)
        self.assertNotIn("Updated", text)

    def test_verbose_rendering_escapes(self):
        snapshots = [
            {
                "name": "AT&T <Token> by March 31, 2026",
                "yes_value": 0.62,
                "no_value": 0.38,
            }
        ]
        text = render_widget_text(snapshots, datetime(2026, 1, 31, 12, 34), compact_mode=False)

        self.assertIn("AT&amp;T &lt;Token&gt;", text)
        self.assertIn("YES: 62%", text)
        self.assertIn("NO: 38%", text)
        self.assertIn("UTC 12:34", text)

    def test_alias_uniqueness(self):
        snapshots = [
            {"name": "Alpha Beta", "yes_value": 0.5, "no_value": 0.5},
            {"name": "Alpha Bitcoin", "yes_value": 0.5, "no_value": 0.5},
            {"name": "Alpha Beta", "yes_value": 0.5, "no_value": 0.5},
        ]
        aliases = generate_market_aliases(snapshots)
        self.assertEqual(len(aliases), len(set(aliases)))

    def test_compact_line_length(self):
        snapshots = [
            {"name": "Super Extra Long Market Name That Keeps Going", "yes_value": 0.01, "no_value": 0.99},
            {"name": "Another Long Market Name", "yes_value": 0.5, "no_value": 0.5},
        ]
        text = render_widget_text(snapshots, datetime(2026, 1, 31, 9, 0))
        lines = text.split("\n")
        for line in lines[1:-1]:
            self.assertLessEqual(len(line), 32)


if __name__ == "__main__":
    unittest.main()
