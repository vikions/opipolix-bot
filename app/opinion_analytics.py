from typing import Dict, List

from opinion_client import client, _get_orderbook_core


def get_market_liquidity(token_id: str) -> str:
    """Calculate liquidity level based on orderbook depth."""
    try:
        book = _get_orderbook_core(token_id)
        if not book:
            return "⚠️ Low"

        asks = getattr(book, "asks", []) or []
        bids = getattr(book, "bids", []) or []
        total_orders = len(asks) + len(bids)

        if total_orders > 20:
            return "💎 High"
        if total_orders > 10:
            return "📊 Medium"
        return "⚠️ Low"
    except Exception:
        return "❓ Unknown"


def get_price_trend(yes_price: float) -> str:
    """Determine market sentiment based on YES price."""
    if yes_price > 0.6:
        return "🔥"
    if yes_price < 0.4:
        return "❄️"
    return "⚖️"


def analyze_market(market_id: int) -> Dict:
    """Get full analytics for a market."""
    try:
        detail = client.get_market(market_id)
        if detail.errno != 0:
            return {"status": "error", "market_id": market_id, "error": detail.errmsg}

        m = detail.result.data

        from opinion_client import get_opinion_binary_prices

        prices = get_opinion_binary_prices(market_id)

        yes_price = prices.get("yes")
        no_price = prices.get("no")

        if yes_price is None or no_price is None:
            return {"status": "error", "market_id": market_id, "error": "Prices unavailable"}

        balance = yes_price + no_price
        balance_status = "✅" if 0.97 <= balance <= 1.03 else "⚠️"
        trend = get_price_trend(yes_price)

        yes_token_id = getattr(m, "yes_token_id", None)
        liquidity = get_market_liquidity(yes_token_id) if yes_token_id else "❓ Unknown"

        return {
            "status": "success",
            "market_id": market_id,
            "title": m.market_title,
            "yes_price": yes_price,
            "no_price": no_price,
            "balance": balance,
            "balance_status": balance_status,
            "trend": trend,
            "liquidity": liquidity,
            "volume": getattr(m, "volume", "N/A"),
        }
    except Exception as exc:
        return {"status": "error", "market_id": market_id, "error": str(exc)}


def format_market_line(idx: int, analytics: Dict, max_title_len: int = 35) -> str:
    """Format single market line."""
    if analytics.get("status") != "success":
        return (
            f"📊 {idx}. Market #{analytics.get('market_id', '?')}\n"
            f"   ❌ {analytics.get('error', 'Unknown error')}\n\n"
        )

    title = analytics["title"]
    if len(title) > max_title_len:
        title = f"{title[:max_title_len]}..."

    yes_price = analytics["yes_price"]
    no_price = analytics["no_price"]
    trend = analytics["trend"]
    balance = analytics["balance"]
    balance_status = analytics["balance_status"]
    liquidity = analytics["liquidity"]

    return (
        f"📊 *{idx}. {title}*\n"
        f"   YES: ${yes_price:.3f} ({yes_price * 100:.0f}%) {trend} | NO: ${no_price:.3f}\n"
        f"   Balance: {balance_status} {balance:.3f} | Liquidity: {liquidity}\n\n"
    )


def get_summary_stats(markets_analytics: List[Dict]) -> str:
    """Calculate summary statistics."""
    total_markets = len(markets_analytics)

    balances = [
        m["balance"] for m in markets_analytics if m.get("status") == "success"
    ]
    avg_balance = sum(balances) / len(balances) if balances else 0

    hottest = None
    max_yes = 0
    for m in markets_analytics:
        if m.get("status") == "success" and m["yes_price"] > max_yes:
            max_yes = m["yes_price"]
            hottest = m["title"][:30]

    health = "healthy" if 0.97 <= avg_balance <= 1.03 else "unstable"

    summary = (
        f"📈 Total Active: {total_markets} markets\n"
        f"💰 Avg Balance: {avg_balance:.3f} ({health})\n"
    )

    if hottest:
        summary += f"🔥 Hottest: {hottest}"

    return summary
