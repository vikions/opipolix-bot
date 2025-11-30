import requests
import json
from typing import List, Dict

# Официальный Gamma endpoint из доки:
# https://docs.polymarket.com/developers/gamma-markets-api/get-markets
BASE_URL = "https://gamma-api.polymarket.com"


def fetch_raw_polymarket_markets(limit: int = 5) -> list:
    """
    Тянем рынки с Gamma API Polymarket (GET /markets).

    Используем параметры из доки:
    - closed=false  → только активные рынки
    - order=id      → сортировка по id
    - ascending=false → новые сначала
    """
    params = {
        "limit": limit,
        "closed": "false",
        "order": "id",
        "ascending": "false",
    }

    resp = requests.get(f"{BASE_URL}/markets", params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    # В Gamma /markets обычно возвращает список рынков
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "markets" in data:
        return data["markets"]
    return []


def get_simple_poly_markets(limit: int = 5) -> List[Dict]:
    """
    Приводим рынки Polymarket к простому виду:
    [{'id': ..., 'title': ...}, ...]
    """
    markets = fetch_raw_polymarket_markets(limit)
    simplified: List[Dict] = []

    for m in markets:
        market_id = m.get("id") or m.get("_id") or m.get("slug")
        question = m.get("question") or m.get("title") or m.get("name")
        if market_id and question:
            simplified.append(
                {
                    "id": market_id,
                    "title": question,
                }
            )

    return simplified

def get_polymarket_binary_prices(market_id: int) -> Dict[str, float | None]:
    """
    Возвращает {'yes': price_or_None, 'no': price_or_None} для бинарного рынка Polymarket.
    Используем Gamma /markets?id=...
    Пытаемся вытащить outcomes + outcomePrices.
    """
    resp = requests.get(
        f"{BASE_URL}/markets",
        params={"id": market_id},
        timeout=10
    )
    resp.raise_for_status()
    data = resp.json()

    if isinstance(data, list):
        markets = data
    elif isinstance(data, dict) and "markets" in data:
        markets = data["markets"]
    else:
        return {"yes": None, "no": None}

    if not markets:
        return {"yes": None, "no": None}

    m = markets[0]

    outcomes = m.get("outcomes")
    prices = m.get("outcomePrices")

    # Иногда эти поля могут быть строками с JSON внутри
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

    try:
        if isinstance(outcomes, list) and isinstance(prices, list) and len(outcomes) == len(prices):
            for o, p in zip(outcomes, prices):
                name = str(o).lower()
                try:
                    val = float(p)
                except Exception:
                    continue

                if "yes" in name:
                    yes_price = val
                elif "no" in name:
                    no_price = val
    except Exception:
        pass

    return {"yes": yes_price, "no": no_price}
