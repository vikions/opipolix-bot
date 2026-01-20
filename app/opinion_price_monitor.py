from typing import Dict, Optional

from opinion_tracked_markets import fetch_market


class OpinionPriceMonitor:
    """Track Opinion YES prices for alert triggers."""

    def __init__(self):
        self.initial_prices: Dict[int, float] = {}
        self.current_prices: Dict[int, float] = {}

    async def get_current_price(self, market_id: int) -> Optional[float]:
        try:
            market = await fetch_market(market_id)
            if not market:
                print(f"[Opinion] No market data for {market_id}")
                return None

            yes_price = market.get("yes_price")
            no_price = market.get("no_price")

            if yes_price is None and no_price is not None and 0 <= no_price <= 1:
                yes_price = 1 - no_price

            if yes_price is None:
                print(f"[Opinion] No YES price for {market_id}")
                return None

            self.current_prices[market_id] = yes_price
            print(f"[Opinion] Current price for {market_id}: ${yes_price:.4f}")

            if market_id not in self.initial_prices:
                self.initial_prices[market_id] = yes_price
                print(f"[Opinion] Initial price for {market_id}: ${yes_price:.4f}")

            return yes_price

        except Exception as e:
            print(f"[Opinion] Error getting price for {market_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def calculate_price_change(self, market_id: int) -> Optional[float]:
        if market_id not in self.initial_prices or market_id not in self.current_prices:
            return None

        initial = self.initial_prices[market_id]
        current = self.current_prices[market_id]

        if initial == 0:
            return None

        return ((current - initial) / initial) * 100

    def reset_initial_price(self, market_id: int):
        if market_id in self.current_prices:
            self.initial_prices[market_id] = self.current_prices[market_id]
            print(
                f"[Opinion] Reset initial price for {market_id}: "
                f"${self.current_prices[market_id]:.4f}"
            )

    async def check_trigger(
        self,
        market_id: int,
        alert_type: str,
        trigger_percent: float
    ) -> bool:
        current_price = await self.get_current_price(market_id)

        if current_price is None:
            return False

        change = self.calculate_price_change(market_id)

        if change is None:
            return False

        if alert_type == "price_pump":
            triggered = change >= trigger_percent
            if triggered:
                print(
                    f"[Opinion] PUMP TRIGGER {market_id}: "
                    f"+{change:.2f}% (target: +{trigger_percent}%)"
                )
        else:
            triggered = change <= -trigger_percent
            if triggered:
                print(
                    f"[Opinion] DUMP TRIGGER {market_id}: "
                    f"{change:.2f}% (target: -{trigger_percent}%)"
                )

        return triggered
