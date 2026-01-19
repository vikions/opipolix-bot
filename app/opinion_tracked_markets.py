import asyncio
import logging
from typing import Dict, List, Optional

from opinion_client import client, _extract_best_ask_price, _get_orderbook_core

logger = logging.getLogger(__name__)

WHITELIST_MARKET_IDS = [
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

REQUEST_TIMEOUT_SEC = 10.0


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


def _count_orders(book: object) -> int:
    asks = getattr(book, "asks", []) or []
    bids = getattr(book, "bids", []) or []
    return len(asks) + len(bids)


def _fetch_market_sync(market_id: int) -> Optional[Dict]:
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

    market = getattr(getattr(detail, "result", None), "data", None)
    if market is None:
        return None

    title = _get_first_attr(market, ["market_title", "marketTitle", "title"])
    if not title:
        return None

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
        "title": title,
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
    tasks = [fetch_market(market_id) for market_id in WHITELIST_MARKET_IDS]
    results = await asyncio.gather(*tasks)
    markets = [market for market in results if market is not None]
    markets.sort(key=lambda m: m.get("volume24h", 0.0), reverse=True)
    return markets


def format_volume(amount: float) -> str:
    if amount >= 1_000_000:
        return f"{amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        scaled = amount / 1_000
        if scaled >= 999.95:
            return f"{amount / 1_000_000:.1f}M"
        return f"{scaled:.1f}k"
    return f"{amount:.0f}"


def format_tracked_markets_message(markets: List[Dict]) -> str:
    lines = [
        "🔥 *OPINION MARKETS (Tracked Token Launch Markets)*",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for idx, market in enumerate(markets, 1):
        lines.append(f"📊 {idx}. {market['title']}")

        yes_price = market.get("yes_price")
        no_price = market.get("no_price")
        yes_pct = market.get("yes_pct")

        if yes_price is not None and no_price is not None:
            pct_text = f" ({yes_pct}%)" if yes_pct is not None else ""
            lines.append(
                f"   YES: ${yes_price:.3f}{pct_text} | NO: ${no_price:.3f}"
            )

        vol_display = format_volume(market.get("volume24h", 0.0))
        orders = market.get("orders")
        orders_display = str(orders) if isinstance(orders, int) else "—"
        lines.append(f"   Vol 24h: ${vol_display} | {orders_display} orders")
        lines.append("")

    return "\n".join(lines).rstrip()
