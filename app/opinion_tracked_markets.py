# -*- coding: utf-8 -*-
import asyncio
import logging
import re
import threading
import time
from typing import Dict, List, Optional, Tuple

from opinion_client import client, _extract_best_ask_price, _get_orderbook_core

logger = logging.getLogger(__name__)

USE_EMOJI = True
SEPARATOR_LINE = "------------------------------"

HEADER_EMOJI = "\U0001F525"
INTRO_EMOJI = "\U0001F4C8"
RANK_EMOJI = "\U0001F4CC"
VOLUME_EMOJI = "\U0001F4B0"

WHITELIST_CHILD_IDS = [
    3410,  # Will Nansen launch a token by March 31, 2026
    2596,  # Will Theo launch a token by March 31, 2026
    3402,  # Will Perena launch a token by March 31, 2026
    2111,  # Will Base launch a token by March 31, 2026
    3341,  # Will Exponent launch a token by March 31, 2026
    3337,  # Will ETHGAS launch a token by March 31, 2026
    3406,  # Will Loopscale launch a token by March 31, 2026
    1797,  # Will Polymarket launch a token by March 31, 2026
    3051,  # Will fomo.family launch a token by March 31, 2026
    2102,  # Will MetaMask launch a token by March 31, 2026
    2607,  # Will Paradex launch a token by February 28, 2026
    2566,  # Will Abstract launch a token by December 31, 2026
    2994,  # Will Tempo launch a token by March 31, 2026
    2561,  # Will Pacifica launch a token by ...?
]

CHILD_TO_PROJECT = {
    3410: "Nansen",
    2596: "Theo",
    3402: "Perena",
    2111: "Base",
    3341: "Exponent",
    3337: "ETHGAS",
    3406: "Loopscale",
    1797: "Polymarket",
    3051: "fomo.family",
    2102: "MetaMask",
    2607: "Paradex",
    2566: "Abstract",
    2994: "Tempo",
    2561: "Pacifica",
}

CHILD_TO_PARENT_ID = {
    # Add parent IDs here if/when they are known.
}

REQUEST_TIMEOUT_SEC = 10.0
PARENT_TITLE_TTL_SEC = 300.0

_PARENT_TITLE_CACHE: Dict[int, Tuple[str, float]] = {}
_PARENT_TITLE_LOCK = threading.Lock()

_MONTH_PATTERN = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
    re.IGNORECASE,
)
_YEAR_PATTERN = re.compile(r"\b20\d{2}\b")
_DATE_WITHOUT_COMMA = re.compile(
    r"\b(?P<month>january|february|march|april|may|june|july|august|september|october|november|december)\s+(?P<day>\d{1,2})\s+(?P<year>20\d{2})\b",
    re.IGNORECASE,
)

INTRO_TEXT = (
    "Hottest token-launch markets on Opinion right now (ranked by 24h volume)."
)


def _get_first_attr(obj: object, names: List[str]) -> Optional[object]:
    for name in names:
        value = getattr(obj, name, None)
        if value is not None:
            return value
    return None


def _coerce_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if not cleaned:
            return default
        try:
            return float(cleaned)
        except ValueError:
            return default
    return default


def _coerce_int(value: object) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if not cleaned:
            return None
        try:
            return int(float(cleaned))
        except ValueError:
            return None
    return None


def _normalize_date_text(text: str) -> str:
    def repl(match: re.Match) -> str:
        return f"{match.group('month')} {match.group('day')}, {match.group('year')}"

    return _DATE_WITHOUT_COMMA.sub(repl, text)


def _looks_like_full_title(title: str, project_name: Optional[str]) -> bool:
    lowered = title.lower()
    if lowered.startswith("will "):
        return True
    if "launch a token" in lowered:
        return True
    if "token by" in lowered:
        return True
    if project_name and project_name.lower() in lowered:
        return True
    return False


def _looks_like_date_title(title: str) -> bool:
    lowered = title.lower()
    if not _MONTH_PATTERN.search(lowered):
        return False
    if not _YEAR_PATTERN.search(lowered):
        return False
    return True


def _combine_parent_child_title(parent_title: str, child_title: str) -> str:
    cleaned = parent_title.strip()
    if cleaned.endswith("?"):
        cleaned = cleaned[:-1].strip()
    cleaned = re.sub(r"\bby\b.*$", "by", cleaned, flags=re.IGNORECASE).strip()
    if not re.search(r"\bby\b$", cleaned, flags=re.IGNORECASE):
        cleaned = f"{cleaned} by"
    return f"{cleaned} {child_title}".strip()


def _get_market_detail_sync(market_id: int) -> Optional[object]:
    try:
        detail = client.get_market(market_id)
    except Exception:
        logger.exception("Opinion get_market failed for %s", market_id)
        return None

    if getattr(detail, "errno", None) != 0:
        logger.warning(
            "Opinion get_market error %s for %s: %s",
            getattr(detail, "errno", None),
            market_id,
            getattr(detail, "errmsg", ""),
        )
        return None

    return getattr(getattr(detail, "result", None), "data", None)


def _get_parent_title_sync(parent_id: int) -> Optional[str]:
    now = time.monotonic()
    with _PARENT_TITLE_LOCK:
        cached = _PARENT_TITLE_CACHE.get(parent_id)
        if cached and cached[1] > now:
            return cached[0]

    parent_market = _get_market_detail_sync(parent_id)
    if parent_market is None:
        return None

    title = _get_first_attr(parent_market, ["market_title", "marketTitle", "title"])
    if not title:
        return None

    with _PARENT_TITLE_LOCK:
        _PARENT_TITLE_CACHE[parent_id] = (title, now + PARENT_TITLE_TTL_SEC)

    return title


def _resolve_full_title(market_id: int, child_title: str, market_obj: object) -> str:
    project_name = CHILD_TO_PROJECT.get(market_id)
    if _looks_like_full_title(child_title, project_name):
        return _normalize_date_text(child_title)

    if not _looks_like_date_title(child_title):
        return _normalize_date_text(child_title)

    normalized_child = _normalize_date_text(child_title)

    parent_id = CHILD_TO_PARENT_ID.get(market_id)
    if parent_id is None:
        parent_id = _get_first_attr(
            market_obj,
            [
                "parent_market_id",
                "parentMarketId",
                "parent_id",
                "parentId",
                "parent",
            ],
        )
    parent_id = _coerce_int(parent_id)

    if parent_id:
        parent_title = _get_parent_title_sync(parent_id)
        if parent_title:
            combined = _combine_parent_child_title(parent_title, normalized_child)
            return _normalize_date_text(combined)

    if project_name:
        return f"Will {project_name} launch a token by {normalized_child}"

    return normalized_child


def _count_orders(book: object) -> int:
    asks = getattr(book, "asks", []) or []
    bids = getattr(book, "bids", []) or []
    return len(asks) + len(bids)


def _fetch_market_sync(market_id: int) -> Optional[Dict]:
    market = _get_market_detail_sync(market_id)
    if market is None:
        return None

    title = _get_first_attr(market, ["market_title", "marketTitle", "title"])
    if not title:
        return None

    full_title = _resolve_full_title(market_id, str(title), market)

    volume_raw = _get_first_attr(
        market, ["volume24h", "volume_24h", "volume24H", "volume"]
    )
    volume24h = _coerce_float(volume_raw, default=0.0)

    orders_raw = _get_first_attr(
        market, ["order_count", "orders_count", "orderCount", "orders"]
    )
    orders_count = _coerce_int(orders_raw)

    yes_token_id = _get_first_attr(market, ["yes_token_id", "yesTokenId"])
    no_token_id = _get_first_attr(market, ["no_token_id", "noTokenId"])

    yes_price = None
    no_price = None
    fallback_orders = 0
    used_orderbooks = False

    if yes_token_id:
        book_yes = _get_orderbook_core(yes_token_id)
        if book_yes is not None:
            yes_price = _extract_best_ask_price(book_yes)
            fallback_orders += _count_orders(book_yes)
            used_orderbooks = True

    if no_token_id:
        book_no = _get_orderbook_core(no_token_id)
        if book_no is not None:
            no_price = _extract_best_ask_price(book_no)
            fallback_orders += _count_orders(book_no)
            used_orderbooks = True

    if orders_count is None and used_orderbooks and fallback_orders > 0:
        orders_count = fallback_orders

    yes_pct = int(round(yes_price * 100)) if yes_price is not None else None

    return {
        "id": market_id,
        "title": full_title,
        "yes_price": yes_price,
        "no_price": no_price,
        "yes_pct": yes_pct,
        "volume24h": volume24h,
        "orders": orders_count,
    }


async def fetch_market(market_id: int) -> Optional[Dict]:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_fetch_market_sync, market_id),
            timeout=REQUEST_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        logger.warning("Opinion get_market timed out for %s", market_id)
        return None
    except Exception:
        logger.exception("Opinion fetch_market failed for %s", market_id)
        return None


async def get_tracked_markets() -> List[Dict]:
    tasks = [fetch_market(market_id) for market_id in WHITELIST_CHILD_IDS]
    results = await asyncio.gather(*tasks)
    markets = [market for market in results if market is not None]
    markets.sort(key=lambda m: m.get("volume24h", 0.0), reverse=True)
    return markets


def format_volume(amount: float) -> str:
    amount = max(amount, 0.0)
    if amount >= 1_000_000:
        return f"{amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        scaled = amount / 1_000
        if scaled >= 999.95:
            return f"{amount / 1_000_000:.1f}M"
        return f"{scaled:.1f}k"
    return f"{amount:.0f}"


def format_tracked_markets_message(markets: List[Dict], limit: Optional[int] = None) -> str:
    shown = markets if limit is None else markets[:limit]

    header = (
        f"{HEADER_EMOJI} OPINION MARKETS (Tracked Token Launch Markets)"
        if USE_EMOJI
        else "OPINION MARKETS (Tracked Token Launch Markets)"
    )
    intro = (
        f"{INTRO_EMOJI} {INTRO_TEXT}"
        if USE_EMOJI
        else INTRO_TEXT
    )

    lines = [
        header,
        SEPARATOR_LINE,
        intro,
        "",
    ]

    for idx, market in enumerate(shown, 1):
        prefix = f"{RANK_EMOJI} {idx}." if USE_EMOJI else f"{idx})"
        lines.append(f"{prefix} {market['title']}")

        yes_price = market.get("yes_price")
        no_price = market.get("no_price")

        if yes_price is None and no_price is not None and 0 <= no_price <= 1:
            yes_price = 1 - no_price
        if no_price is None and yes_price is not None and 0 <= yes_price <= 1:
            no_price = 1 - yes_price

        if yes_price is not None and no_price is not None:
            yes_pct = market.get("yes_pct")
            if yes_pct is None:
                yes_pct = int(round(yes_price * 100))
            lines.append(
                f"   YES: ${yes_price:.3f} ({yes_pct}%) | NO: ${no_price:.3f}"
            )

        vol_display = format_volume(market.get("volume24h", 0.0))
        orders = market.get("orders")
        orders_display = str(orders) if isinstance(orders, int) else "\u2014"
        vol_label = f"{VOLUME_EMOJI} Vol 24h" if USE_EMOJI else "Vol 24h"
        lines.append(f"   {vol_label}: ${vol_display} | {orders_display} orders")
        lines.append("")

    return "\n".join(lines).rstrip()
