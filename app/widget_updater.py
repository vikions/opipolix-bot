from datetime import datetime
from typing import Dict, Optional

from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError

from widget_markets import get_market_snapshots
from widget_renderer import compute_render_hash, render_widget_text


async def update_widget_message(bot, widget: Dict[str, object], db, force: bool = False) -> Dict[str, object]:
    now = datetime.utcnow()
    interval_seconds = int(widget.get("interval_seconds") or 60)
    last_rendered_at = widget.get("last_rendered_at")

    if not force and last_rendered_at:
        delta = (now - last_rendered_at).total_seconds()
        if delta < interval_seconds:
            return {"status": "skipped", "reason": "throttled", "retry_in": interval_seconds - delta}

    selected = widget.get("selected_market_ids") or []
    snapshots = await get_market_snapshots(selected)
    if not snapshots:
        return {"status": "skipped", "reason": "no_data"}

    compare_time = last_rendered_at or now
    compare_text = render_widget_text(snapshots, compare_time)
    compare_hash = compute_render_hash(compare_text)

    if not force and widget.get("last_render_hash") == compare_hash:
        return {"status": "skipped", "reason": "unchanged"}

    render_text = render_widget_text(snapshots, now)
    render_hash = compute_render_hash(render_text)

    try:
        await bot.edit_message_text(
            chat_id=widget.get("target_chat_id"),
            message_id=widget.get("board_message_id"),
            text=render_text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except RetryAfter as exc:
        return {"status": "retry_after", "retry_after": exc.retry_after}
    except (Forbidden, BadRequest) as exc:
        return {"status": "permission_error", "error": str(exc)}
    except TelegramError as exc:
        return {"status": "error", "error": str(exc)}

    db.update_render_state(int(widget.get("widget_id")), render_hash, now)
    return {"status": "updated", "render_text": render_text}
