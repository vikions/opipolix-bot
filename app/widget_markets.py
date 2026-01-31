import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from market_config import get_market
from opinion_tracked_markets import fetch_market as fetch_opinion_market
from polymarket_client import get_polymarket_binary_prices
from polymarket_tracked_markets import fetch_market


async def get_market_snapshot(alias: str) -> Optional[Dict[str, object]]:
    market = get_market(alias)
    if not market:
        return None

    market_id = market.get("polymarket_id")
    opinion_id = market.get("opinion_id")
    title = market.get("title") or alias
    yes_value = None
    no_value = None

    if market_id:
        data = await fetch_market(market_id)
        if data:
            title = data.get("title") or title
            yes_value = data.get("yes_price")
            no_value = data.get("no_price")
    elif opinion_id:
        data = await fetch_opinion_market(opinion_id)
        if data:
            title = data.get("title") or title
            yes_value = data.get("yes_price")
            no_value = data.get("no_price")

    if market_id and (yes_value is None or no_value is None):
        try:
            prices = get_polymarket_binary_prices(market_id)
        except Exception:
            prices = {}
        if yes_value is None:
            yes_value = prices.get("yes")
        if no_value is None:
            no_value = prices.get("no")

    if yes_value is not None and no_value is None:
        try:
            no_value = 1 - float(yes_value)
        except (TypeError, ValueError):
            no_value = None
    if no_value is not None and yes_value is None:
        try:
            yes_value = 1 - float(no_value)
        except (TypeError, ValueError):
            yes_value = None

    return {
        "market_id": market_id or alias,
        "alias": alias,
        "name": title,
        "yes_value": yes_value,
        "no_value": no_value,
        "updated_at": datetime.utcnow(),
    }


async def get_market_snapshots(aliases: List[str]) -> List[Dict[str, object]]:
    tasks = [get_market_snapshot(alias) for alias in aliases]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    snapshots: List[Dict[str, object]] = []
    for alias, result in zip(aliases, results):
        if isinstance(result, Exception) or result is None:
            market = get_market(alias)
            if not market:
                continue
            snapshots.append(
                {
                    "market_id": market.get("polymarket_id") or alias,
                    "alias": alias,
                    "name": market.get("title") or alias,
                    "yes_value": None,
                    "no_value": None,
                    "updated_at": datetime.utcnow(),
                }
            )
        else:
            snapshots.append(result)

    return snapshots
