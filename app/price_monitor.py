"""
Price Monitor для Auto-Trade
Отслеживает цены и срабатывание триггеров
"""
import asyncio
from typing import Dict, Optional
from py_clob_client.client import ClobClient
from market_config import get_market
from database import Database


class PriceMonitor:
    """Мониторинг цен для Auto-Trade"""
    
    def __init__(self):
        self.db = Database()
        # Кеш начальных цен для каждого маркета
        self.initial_prices: Dict[str, float] = {}
        # Кеш последних цен
        self.current_prices: Dict[str, float] = {}
    
    async def get_current_price(self, market_alias: str, outcome: str = 'yes') -> Optional[float]:
        """
        Получить текущую цену маркета
        
        Args:
            market_alias: 'metamask' или 'base'
            outcome: 'yes' или 'no'
        
        Returns:
            float: Текущая цена (0.0 - 1.0) или None
        """
        try:
            # Используем Gamma API (как в polymarket_client!)
            from polymarket_client import get_polymarket_binary_prices
            
            market = get_market(market_alias)
            polymarket_id = market.get('polymarket_id')
            
            if not polymarket_id:
                print(f"❌ No polymarket_id for {market_alias}")
                return None
            
            # Получаем цены через Gamma API
            prices = get_polymarket_binary_prices(polymarket_id)
            price = prices.get(outcome)
            
            if price is None:
                print(f"❌ No price for {market_alias} {outcome.upper()}")
                return None
            
            print(f"📊 Price from Gamma API for {market_alias} {outcome.upper()}: ${price:.4f}")
            
            # Кешируем
            cache_key = f"{market_alias}_{outcome}"
            self.current_prices[cache_key] = price
            
            # Если это первое получение - сохраняем как initial
            if cache_key not in self.initial_prices:
                self.initial_prices[cache_key] = price
                print(f"📊 Initial price for {market_alias} {outcome.upper()}: ${price:.4f}")
            
            return price
            
        except Exception as e:
            print(f"❌ Error getting price for {market_alias} {outcome}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def calculate_price_change(
        self,
        market_alias: str,
        outcome: str = 'yes'
    ) -> Optional[float]:
        """
        Вычислить изменение цены в %
        
        Returns:
            float: Процент изменения (положительный = рост, отрицательный = падение)
        """
        cache_key = f"{market_alias}_{outcome}"
        
        if cache_key not in self.initial_prices or cache_key not in self.current_prices:
            return None
        
        initial = self.initial_prices[cache_key]
        current = self.current_prices[cache_key]
        
        if initial == 0:
            return None
        
        # Процент изменения
        change_percent = ((current - initial) / initial) * 100
        
        return change_percent
    
    def reset_initial_price(self, market_alias: str, outcome: str = 'yes'):
        """Сбросить начальную цену (например после срабатывания триггера)"""
        cache_key = f"{market_alias}_{outcome}"
        if cache_key in self.current_prices:
            self.initial_prices[cache_key] = self.current_prices[cache_key]
            print(f"🔄 Reset initial price for {market_alias} {outcome.upper()}: ${self.current_prices[cache_key]:.4f}")
    
    async def check_trigger(
        self,
        market_alias: str,
        trigger_type: str,
        trigger_value: float
    ) -> bool:
        """
        Проверить сработал ли триггер
        
        Args:
            market_alias: 'metamask' или 'base'
            trigger_type: 'price_pump_YES', 'price_pump_NO', 'price_dump_NO'
            trigger_value: Процент изменения для срабатывания
        
        Returns:
            bool: True если триггер сработал
        """
        # Парсим trigger_type
        if 'YES' in trigger_type:
            outcome = 'yes'
        else:
            outcome = 'no'
        
        # Получаем текущую цену
        current_price = await self.get_current_price(market_alias, outcome)
        
        if current_price is None:
            return False
        
        # Вычисляем изменение
        change = self.calculate_price_change(market_alias, outcome)
        
        if change is None:
            return False
        
        # Проверяем триггер
        if 'pump' in trigger_type:
            # Pump - ждём роста
            triggered = change >= trigger_value
            if triggered:
                print(f"🚀 PUMP TRIGGER! {market_alias} {outcome.upper()}: +{change:.2f}% (target: +{trigger_value}%)")
        else:
            # Dump - ждём падения
            triggered = change <= -trigger_value  # Используем отрицательное значение
            if triggered:
                print(f"📉 DUMP TRIGGER! {market_alias} {outcome.upper()}: {change:.2f}% (target: -{trigger_value}%)")
        
        return triggered
