
from typing import Dict, Literal
from database import Database


class AutoTradeManager:
    """Auto-orders manager"""
    
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
        Create an auto-order
        
        Args:
            telegram_id: User's Telegram ID
            market_alias: 'metamask' or 'base'
            order_type: Order type
                - 'buy_yes_pump': Buy YES on pump
                - 'buy_no_pump': Buy NO on pump (fake news)
                - 'buy_no_dump': Buy NO on dump (safety net)
            trigger_percent: Percentage change (e.g. 15.0 for +15%)
            amount_usdc: Amount in USDC
        
        Returns:
            int: Created order ID
        """
        # Determine side and trigger_type
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
        
        # Save to DB
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
        """Get user's active orders"""
        orders = self.db.get_user_auto_orders(telegram_id)
        return orders
    
    def cancel_order(self, order_id: int) -> bool:
        """Cancel an order"""
        self.db.update_auto_order_status(order_id, 'cancelled')
        print(f"❌ Cancelled auto-order #{order_id}")
        return True
    
    def format_order_info(self, order: Dict) -> str:
        """
        Format order information for display
        
        Args:
            order: Dict from DB
        
        Returns:
            str: Formatted description
        """
        trigger_type = order['trigger_type']
        trigger_value = order['trigger_value']
        amount = order['amount']
        market = order['market_alias'].title()
        
        # Parse type
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
