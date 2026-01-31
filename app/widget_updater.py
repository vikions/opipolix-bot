from datetime import datetime
from typing import Dict

from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError

from widget_markets import get_market_snapshots
from widget_renderer import compute_market_hash, render_widget_text


HEARTBEAT_SECONDS = 600


def decide_widget_update(
    now: datetime,
    last_render_hash: str | None,
    last_heartbeat_at: datetime | None,
    market_hash: str,
    heartbeat_seconds: int = HEARTBEAT_SECONDS,
) -> str:
    if market_hash != last_render_hash:
        return "data_changed"
    if not last_heartbeat_at:
        return "heartbeat"
    elapsed = (now - last_heartbeat_at).total_seconds()
    if elapsed >= heartbeat_seconds:
        return "heartbeat"
    return "skip"


async def update_widget_message(bot, widget: Dict[str, object], db, force: bool = False) -> Dict[str, object]:
    now = datetime.utcnow()
    interval_seconds = int(widget.get("interval_seconds") or 60)
    last_rendered_at = widget.get("last_rendered_at")

    if not force and last_rendered_at:
        delta = (now - last_rendered_at).total_seconds()
        if delta < interval_seconds:
            return {
                "status": "skipped",
                "reason": "throttled",
                "retry_in": interval_seconds - delta,
            }

    selected = widget.get("selected_market_ids") or []
    snapshots = await get_market_snapshots(selected)
    if not snapshots:
        return {"status": "skipped", "reason": "no_data"}

    compact_mode = bool(widget.get("compact_mode", True))
    market_hash = compute_market_hash(snapshots, compact_mode=compact_mode)

    decision = decide_widget_update(
        now=now,
        last_render_hash=widget.get("last_render_hash"),
        last_heartbeat_at=widget.get("last_heartbeat_at"),
        market_hash=market_hash,
    )

    if force:
        decision = "force"

    if decision == "skip":
        return {"status": "skipped", "reason": "unchanged"}

    render_text = render_widget_text(snapshots, now, compact_mode=compact_mode)

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

    db.update_render_state(
        int(widget.get("widget_id")),
        market_hash,
        now,
        heartbeat_at=now,
    )
    return {"status": "updated", "render_text": render_text, "reason": decision}
