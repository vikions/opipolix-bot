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


def get_orderbook_stats(token_id: str) -> Dict:
    """Get orderbook statistics - total orders and depth."""
    try:
        book = _get_orderbook_core(token_id)
        if not book:
            return {"orders": 0, "depth": "0"}

        asks = getattr(book, "asks", []) or []
        bids = getattr(book, "bids", []) or []
        total_orders = len(asks) + len(bids)

        depth = 0
        for ask in asks:
            size = getattr(ask, "size", 0) or getattr(ask, "amount", 0)
            if size:
                try:
                    depth += float(size)
                except Exception:
                    pass

        for bid in bids:
            size = getattr(bid, "size", 0) or getattr(bid, "amount", 0)
            if size:
                try:
                    depth += float(size)
                except Exception:
                    pass

        return {
            "orders": total_orders,
            "depth": f"{depth:.1f}" if depth > 0 else "0",
        }
    except Exception:
        return {"orders": 0, "depth": "0"}


def analyze_market(market_id: int) -> Dict:
    """Get full analytics for a market."""
    try:
        detail = client.get_market(market_id)
        if detail.errno != 0:
            return {"status": "error", "market_id": market_id, "error": detail.errmsg}

        m = detail.result.data
        title = m.market_title

        from opinion_client import get_opinion_binary_prices

        prices = get_opinion_binary_prices(market_id)

        yes_price = prices.get("yes")
        no_price = prices.get("no")

        if yes_price is None or no_price is None:
            return {
                "status": "error",
                "market_id": market_id,
                "title": title,
                "error": "Prices unavailable",
            }

        trend = get_price_trend(yes_price)

        volume = getattr(m, "volume", "0")
        yes_token_id = getattr(m, "yes_token_id", None)

        orderbook_stats = (
            get_orderbook_stats(yes_token_id)
            if yes_token_id
            else {"orders": 0, "depth": "0"}
        )
        orders_count = orderbook_stats["orders"]

        return {
            "status": "success",
            "market_id": market_id,
            "title": title,
            "yes_price": yes_price,
            "no_price": no_price,
            "trend": trend,
            "volume": volume,
            "orders_count": orders_count,
        }
    except Exception as exc:
        return {"status": "error", "market_id": market_id, "error": str(exc)}


def format_market_line(idx: int, analytics: Dict, max_title_len: int = 40) -> str:
    """Format single market line."""
    if analytics.get("status") != "success":
        error_msg = analytics.get("error", "Unknown error")
        title = analytics.get("title", f"Market #{analytics.get('market_id', '?')}")
        return f"📊 {idx}. {title[:max_title_len]}...\n   ❌ {error_msg}\n\n"

    title = analytics["title"]
    if len(title) > max_title_len:
        title = f"{title[:max_title_len]}..."

    yes_price = analytics["yes_price"]
    no_price = analytics["no_price"]
    trend = analytics["trend"]
    volume = analytics.get("volume", "0")
    orders_count = analytics.get("orders_count", 0)

    try:
        vol_num = float(volume)
        if vol_num >= 1000:
            vol_display = f"${vol_num/1000:.1f}k"
        else:
            vol_display = f"${vol_num:.0f}"
    except Exception:
        vol_display = "$0"

    return (
        f"📊 *{idx}. {title}*\n"
        f"   YES: ${yes_price:.3f} ({yes_price * 100:.0f}%) {trend} | NO: ${no_price:.3f}\n"
        f"   Vol 24h: {vol_display} | {orders_count} orders\n\n"
    )


def get_summary_stats(markets_analytics: List[Dict], total_available: int) -> str:
    """Calculate summary statistics."""
    analyzed = len(markets_analytics)
    successful = len([m for m in markets_analytics if m.get("status") == "success"])

    hottest = None
    max_vol = 0
    for m in markets_analytics:
        if m.get("status") == "success":
            try:
                vol = float(m.get("volume", 0))
                if vol > max_vol:
                    max_vol = vol
                    hottest = m["title"][:30]
            except Exception:
                pass

    summary = (
        f"📈 Showing: Top {analyzed} / {total_available} total\n"
        f"✅ Active: {successful} markets\n"
    )

    if hottest:
        if max_vol >= 1000:
            vol_str = f"${max_vol/1000:.1f}k"
        else:
            vol_str = f"${max_vol:.0f}"
        summary += f"🔥 Top volume: {hottest} ({vol_str})"

    return summary
