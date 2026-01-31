import unittest
from datetime import datetime

from app.widget_renderer import compute_render_hash, render_widget_text


class WidgetHashingTest(unittest.TestCase):
    def test_hash_changes_on_value_update(self):
        snapshots = [
            {"name": "MetaMask Token", "yes_value": 0.55, "no_value": 0.45}
        ]
        render_time = datetime(2026, 1, 31, 12, 0)
        text = render_widget_text(snapshots, render_time)
        hash_a = compute_render_hash(text)
        hash_b = compute_render_hash(render_widget_text(snapshots, render_time))

        self.assertEqual(hash_a, hash_b)

        snapshots_changed = [
            {"name": "MetaMask Token", "yes_value": 0.60, "no_value": 0.40}
        ]
        hash_c = compute_render_hash(render_widget_text(snapshots_changed, render_time))
        self.assertNotEqual(hash_a, hash_c)


if __name__ == "__main__":
    unittest.main()
