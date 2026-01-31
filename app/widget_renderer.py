import hashlib
import html
from datetime import datetime
from typing import Dict, List, Optional


def short_market_title(title: str) -> str:
    if not title:
        return "Market"
    cleaned = title.strip()
    if " by " in cleaned:
        cleaned = cleaned.split(" by ", 1)[0].strip()
    if " one day after " in cleaned:
        cleaned = cleaned.split(" one day after ", 1)[0].strip()
    if cleaned.endswith("?"):
        cleaned = cleaned[:-1].strip()
    if len(cleaned) > 40:
        cleaned = f"{cleaned[:37].rstrip()}..."
    return cleaned


def format_value(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if numeric < 0:
        numeric = 0.0
    if numeric > 1:
        percent = numeric
    else:
        percent = numeric * 100
    return f"{percent:.1f}%"


def render_widget_text(snapshots: List[Dict[str, object]], updated_at: datetime) -> str:
    lines = ["<b>📌 OpiPolix Widget</b>"]

    for snapshot in snapshots:
        name = snapshot.get("name") or "Market"
        short_name = short_market_title(str(name))
        safe_name = html.escape(short_name)
        yes_value = format_value(snapshot.get("yes_value"))
        no_value = format_value(snapshot.get("no_value"))

        lines.append(safe_name)
        lines.append(f"🟢 YES: {yes_value}   🔴 NO: {no_value}")

    time_str = updated_at.strftime("%H:%M UTC")
    lines.append(f"Updated: {time_str}")
    return "\n".join(lines)


def compute_render_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_render_hash_for_time(
    snapshots: List[Dict[str, object]], render_time: datetime
) -> str:
    text = render_widget_text(snapshots, render_time)
    return compute_render_hash(text)
