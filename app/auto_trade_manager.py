"""
Auto-Trade Manager для OpiPoliX бота
Управление автоматическими ордерами
"""
from typing import Dict, Literal
from database import Database


class AutoTradeManager:
    """Менеджер авто-ордеров"""
    
    def __init__(self):
        self.db = Database()
    
    def create_order(
        self,
        telegram_id: int,
        market_alias: str,
        order_type: Literal['buy_yes_pump', 'buy_no_pump', 'buy_no_dump'],
        trigger_percent: float,
        amount_usdc: float
    ) -> int:
        """
        Создать авто-ордер
        
        Args:
            telegram_id: ID пользователя
            market_alias: 'metamask' или 'base'
            order_type: Тип ордера
                - 'buy_yes_pump': Купить YES при pump
                - 'buy_no_pump': Купить NO при pump (fake news)
                - 'buy_no_dump': Купить NO при dump (страховка)
            trigger_percent: Процент изменения (например 15.0 для +15%)
            amount_usdc: Сумма в USDC
        
        Returns:
            int: ID созданного ордера
        """
        # Определяем side и trigger_type
        if order_type == 'buy_yes_pump':
            side = 'BUY'
            outcome = 'YES'
            trigger_type = 'price_pump'
        elif order_type == 'buy_no_pump':
            side = 'BUY'
            outcome = 'NO'
            trigger_type = 'price_pump'
        elif order_type == 'buy_no_dump':
            side = 'BUY'
            outcome = 'NO'
            trigger_type = 'price_dump'
        else:
            raise ValueError(f"Unknown order type: {order_type}")
        
        # Сохраняем в БД
        order_id = self.db.create_auto_order(
            telegram_id=telegram_id,
            market_alias=market_alias,
            trigger_type=f"{trigger_type}_{outcome}",  # price_pump_YES, price_dump_NO
            trigger_value=trigger_percent,
            side=side,
            amount=amount_usdc
        )
        
        print(f"✅ Created auto-order #{order_id}: {order_type} {trigger_percent}% ${amount_usdc}")
        
        return order_id
    
    def get_user_orders(self, telegram_id: int) -> list:
        """Получить активные ордера пользователя"""
        orders = self.db.get_user_auto_orders(telegram_id)
        return orders
    
    def cancel_order(self, order_id: int) -> bool:
        """Отменить ордер"""
        self.db.update_auto_order_status(order_id, 'cancelled')
        print(f"❌ Cancelled auto-order #{order_id}")
        return True
    
    def format_order_info(self, order: Dict) -> str:
        """
        Форматировать информацию об ордере для отображения
        
        Args:
            order: Dict из БД
        
        Returns:
            str: Форматированное описание
        """
        trigger_type = order['trigger_type']
        trigger_value = order['trigger_value']
        amount = order['amount']
        market = order['market_alias'].title()
        
        # Парсим тип
        if 'pump_YES' in trigger_type:
            emoji = "📈"
            description = f"Buy YES on +{trigger_value}% pump"
        elif 'pump_NO' in trigger_type:
            emoji = "🎭"
            description = f"Buy NO on +{trigger_value}% pump (fake news)"
        elif 'dump_NO' in trigger_type:
            emoji = "📉"
            description = f"Buy NO on -{trigger_value}% dump"
        else:
            emoji = "❓"
            description = f"Unknown type: {trigger_type}"
        
        return (
            f"{emoji} *{market}* - {description}\n"
            f"💰 Amount: ${amount:.2f}\n"
            f"🆔 Order ID: `{order['id']}`"
        )
