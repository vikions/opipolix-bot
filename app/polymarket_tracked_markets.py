# -*- coding: utf-8 -*-
import asyncio
import json
import logging
from typing import Dict, List, Optional

import requests

from market_config import get_market

logger = logging.getLogger(__name__)

BASE_URL = "https://gamma-api.polymarket.com"
REQUEST_TIMEOUT_SEC = 10.0
SEPARATOR_LINE = "------------------------------"

ALIASES_FROM_CONFIG = ["base", "metamask", "abstract", "extended", "megaeth", "opinion", "opensea"]

EXTRA_MARKETS = [
    {
        "polymarket_id": 706859,
        "slug": "will-theo-launch-a-token-by-march-31-2026",
    },
    {
        "polymarket_id": 664878,
        "slug": "will-consensys-ipo-by-march-31-2026",
    },
    {
        "polymarket_id": 697523,
        "slug": "will-unit-launch-a-token-by-december-31-2026",
    },
    {
        "polymarket_id": 704135,
        "slug": "will-tempo-launch-a-token-by-march-31-2026",
    },
    {
        "polymarket_id": 1068689,
        "slug": "will-phantom-launch-a-token-by-march-31-2026",
    },
    {
        "polymarket_id": 1122084,
        "slug": "okx-ipo-in-2026",
    },
    {
        "polymarket_id": 690689,
        "slug": "will-pacifica-launch-a-token-by-march-31-2026",
    },
    {
        "polymarket_id": 1038566,
        "slug": "will-nansen-launch-a-token-by-june-30-2026",
    },
    {
        "polymarket_id": 1068681,
        "slug": "will-rabby-launch-a-token-by-march-31-2026",
    },
    {
        "polymarket_id": 1038641,
        "slug": "will-loopscale-launch-a-token-by-june-30-2026",
    },
]

SPECIAL_WORDS = {
    "okx": "OKX",
    "ipo": "IPO",
    "fdv": "FDV",
    "opensea": "OpenSea",
    "metamask": "MetaMask",
    "polymarket": "Polymarket",
    "usdc": "USDC",
}

LOWERCASE_WORDS = {
    "a",
    "an",
    "the",
    "by",
    "in",
    "of",
    "to",
    "on",
    "one",
    "day",
    "after",
}


def _format_slug_title(slug: Optional[str]) -> Optional[str]:
    if not slug:
        return None
    words = [w for w in slug.replace("_", "-").split("-") if w]
    if not words:
        return None

    formatted: List[str] = []
    for idx, word in enumerate(words):
        lowered = word.lower()
        if lowered in SPECIAL_WORDS:
            output = SPECIAL_WORDS[lowered]
        elif idx > 0 and lowered in LOWERCASE_WORDS:
            output = lowered
        else:
            output = lowered.capitalize()
        formatted.append(output)

    title = " ".join(formatted)
    if words[0].lower() == "will" and not title.endswith("?"):
        title = f"{title}?"
    return title


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


def _parse_prices(market: Dict[str, object]) -> tuple[Optional[float], Optional[float]]:
    outcomes = market.get("outcomes")
    prices = market.get("outcomePrices")

    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except Exception:
            outcomes = None
    if isinstance(prices, str):
        try:
            prices = json.loads(prices)
        except Exception:
            prices = None

    yes_price = None
    no_price = None

    if isinstance(outcomes, list) and isinstance(prices, list):
        for outcome, price in zip(outcomes, prices):
            name = str(outcome).lower()
            try:
                val = float(price)
            except Exception:
                continue
            if "yes" in name:
                yes_price = val
            elif "no" in name:
                no_price = val

    if yes_price is None and no_price is not None and 0 <= no_price <= 1:
        yes_price = 1 - no_price
    if no_price is None and yes_price is not None and 0 <= yes_price <= 1:
        no_price = 1 - yes_price

    return yes_price, no_price


def _fetch_market_sync(market_id: int) -> Optional[Dict]:
    try:
        resp = requests.get(
            f"{BASE_URL}/markets",
            params={"id": market_id},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        logger.exception("Polymarket get_market failed for %s", market_id)
        return None

    if isinstance(data, list):
        markets = data
    elif isinstance(data, dict) and "markets" in data:
        markets = data["markets"]
    else:
        return None

    if not markets:
        return None

    market = markets[0]
    title = market.get("question") or market.get("title") or market.get("name")
    slug = market.get("slug")
    # Use explicit 24h fields only; do not fallback to total volume.
    volume_raw = (
        market.get("volume24hrClob")
        or market.get("volume24hr")
        or market.get("volume24h")
        or market.get("volume_24h")
    )
    volume24h = _coerce_float(volume_raw, default=0.0)
    yes_price, no_price = _parse_prices(market)
    yes_pct = int(round(yes_price * 100)) if yes_price is not None else None

    return {
        "id": market_id,
        "title": title,
        "slug": slug,
        "yes_price": yes_price,
        "no_price": no_price,
        "yes_pct": yes_pct,
        "volume24h": volume24h,
    }


async def fetch_market(market_id: int) -> Optional[Dict]:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_fetch_market_sync, market_id),
            timeout=REQUEST_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        logger.warning("Polymarket get_market timed out for %s", market_id)
        return None
    except Exception:
        logger.exception("Polymarket fetch_market failed for %s", market_id)
        return None


def _build_tracked_markets() -> List[Dict]:
    markets: List[Dict] = []

    for alias in ALIASES_FROM_CONFIG:
        market = get_market(alias)
        if not market:
            continue
        market_id = market.get("polymarket_id")
        if not market_id:
            continue
        markets.append(
            {
                "polymarket_id": market_id,
                "slug": market.get("slug"),
                "title": market.get("title"),
            }
        )

    markets.extend(EXTRA_MARKETS)

    seen_ids = set()
    unique: List[Dict] = []
    for market in markets:
        market_id = market.get("polymarket_id")
        if market_id in seen_ids or market_id is None:
            continue
        seen_ids.add(market_id)
        unique.append(market)

    return unique


async def get_tracked_markets() -> List[Dict]:
    tracked = _build_tracked_markets()
    tasks = [fetch_market(market["polymarket_id"]) for market in tracked]
    results = await asyncio.gather(*tasks)

    markets: List[Dict] = []
    for market, fallback in zip(results, tracked):
        if market is None:
            continue
        title = market.get("title")
        if not title:
            title = fallback.get("title") or _format_slug_title(fallback.get("slug"))
        if not title:
            title = f"Market #{fallback.get('polymarket_id')}"
        market["title"] = title
        markets.append(market)

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

    lines = [
        "POLYMARKET MARKETS (Tracked Token Launch Markets)",
        SEPARATOR_LINE,
        "Top tracked Polymarket markets ranked by 24h volume.",
        "",
    ]

    for idx, market in enumerate(shown, 1):
        lines.append(f"{idx}. {market['title']}")

        yes_price = market.get("yes_price")
        no_price = market.get("no_price")
        yes_pct = market.get("yes_pct")

        if yes_price is not None and no_price is not None:
            if yes_pct is None:
                yes_pct = int(round(yes_price * 100))
            lines.append(
                f"   YES: ${yes_price:.3f} ({yes_pct}%) | NO: ${no_price:.3f}"
            )

        vol_display = format_volume(market.get("volume24h", 0.0))
        lines.append(f"   Vol 24h: ${vol_display}")
        lines.append("")

    return "\n".join(lines).rstrip()
