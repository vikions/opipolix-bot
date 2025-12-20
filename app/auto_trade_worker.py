
import asyncio
import os
from typing import Optional
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError

from database import Database
from price_monitor import PriceMonitor
from auto_trade_manager import AutoTradeManager
from wallet_manager import WalletManager
from market_config import get_market
from clob_trading import trade_market


class AutoTradeWorker:
    
    
    def __init__(self, telegram_token: str):
        self.db = Database()
        self.price_monitor = PriceMonitor()
        self.auto_trade_manager = AutoTradeManager()
        self.wallet_manager = WalletManager()
        self.bot = Bot(token=telegram_token)
        
        # Интервал проверки (секунды)
        self.check_interval = 10
        
        print("🤖 Auto-Trade Worker initialized!")
    
    async def send_notification(self, telegram_id: int, message: str):
        
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode="Markdown"
            )
            print(f"✉️ Notification sent to user {telegram_id}")
        except TelegramError as e:
            print(f"❌ Failed to send notification to {telegram_id}: {e}")
    
    async def execute_order_with_retry(
        self,
        order: dict,
        max_retries: int = 3
    ) -> dict:
        """
             
        Args:
            order: Dict из БД
            max_retries: Максимум попыток
        
        Returns:
            dict: {'status': 'success'/'failed', 'attempts': int, ...}
        """
        telegram_id = order['telegram_id']
        market_alias = order['market_alias']
        amount_usdc = order['amount']
        trigger_type = order['trigger_type']
        
       
        if 'YES' in trigger_type:
            outcome = 'yes'
        else:
            outcome = 'no'
        
        market = get_market(market_alias)
        token_id = market['tokens'][outcome]
        
       
        wallet = self.wallet_manager.get_wallet(telegram_id)
        if not wallet or not wallet['safe_address']:
            return {
                'status': 'failed',
                'error': 'No wallet found',
                'attempts': 0
            }
        
        
        private_key = self.wallet_manager.get_private_key(telegram_id)
        
        
        for attempt in range(1, max_retries + 1):
            
            retry_amount = amount_usdc / (2 ** (attempt - 1))
            
            if retry_amount < 1:
                retry_amount = 1  
            
            print(f"🔄 Attempt {attempt}/{max_retries}: Trying ${retry_amount:.2f}")
            
            
            if attempt == 1:
                await self.send_notification(
                    telegram_id,
                    f"🤖 *Auto-Trade Triggered!*\n\n"
                    f"{market['emoji']} {market['title']}\n"
                    f"📊 Buying {outcome.upper()}\n"
                    f"💰 Amount: ${retry_amount:.2f}\n\n"
                    f"⏳ Executing..."
                )
            else:
                await self.send_notification(
                    telegram_id,
                    f"⏳ Attempt {attempt}/{max_retries}\n"
                    f"Trying ${retry_amount:.2f}..."
                )
            
            try:
                
                result = trade_market(
                    user_private_key=private_key,
                    token_id=token_id,
                    side="BUY",
                    amount_usdc=retry_amount,
                    telegram_id=telegram_id,
                    funder_address=wallet['safe_address']  
                )
                
                if result['status'] == 'success':
                    
                    print(f"✅ Order executed successfully on attempt {attempt}")
                    
                    await self.send_notification(
                        telegram_id,
                        f"✅ *Auto-Trade Successful!*\n\n"
                        f"{market['emoji']} {market['title']}\n"
                        f"📊 Bought {outcome.upper()}\n"
                        f"💰 Amount: ${retry_amount:.2f}\n"
                        f"🎯 Attempts: {attempt}\n\n"
                        f"⚡ Gasless transaction!\n"
                        f"🏆 Attributed to OpiPoliX!"
                    )
                    
                    return {
                        'status': 'success',
                        'attempts': attempt,
                        'amount_executed': retry_amount,
                        'order_id': result.get('order_id')
                    }
                
                else:
                    
                    error = result.get('error', 'Unknown error')
                    print(f"❌ Attempt {attempt} failed: {error}")
                    
                    if attempt < max_retries:
                        
                        await asyncio.sleep(3 * attempt)
                    
            except Exception as e:
                print(f"❌ Exception on attempt {attempt}: {e}")
                
                if attempt < max_retries:
                    await asyncio.sleep(3 * attempt)
        
        
        print(f"❌ All {max_retries} attempts failed")
        
        await self.send_notification(
            telegram_id,
            f"❌ *Auto-Trade Failed*\n\n"
            f"{market['emoji']} {market['title']}\n"
            f"📊 Could not buy {outcome.upper()}\n\n"
            f"🔍 Reason: Low liquidity\n"
            f"💡 Try manual trade or lower amount\n\n"
            f"Order ID: `{order['id']}`"
        )
        
        return {
            'status': 'failed',
            'attempts': max_retries,
            'error': 'All retries failed'
        }
    
    async def check_and_execute_orders(self):
        """Проверить все активные ордера и выполнить если триггер сработал"""
        
        
        active_orders = self.db.get_active_auto_orders()
        
        if not active_orders:
            return
        
        print(f"🔍 Checking {len(active_orders)} active orders...")
        
        for order in active_orders:
            try:
                market_alias = order['market_alias']
                trigger_type = order['trigger_type']
                trigger_value = order['trigger_value']
                
                
                triggered = await self.price_monitor.check_trigger(
                    market_alias=market_alias,
                    trigger_type=trigger_type,
                    trigger_value=trigger_value
                )
                
                if triggered:
                    print(f"🚀 TRIGGER HIT! Order #{order['id']}")
                    
                    
                    result = await self.execute_order_with_retry(order)
                    
                    
                    if result['status'] == 'success':
                        self.db.update_auto_order_status(order['id'], 'executed')
                        print(f"✅ Order #{order['id']} executed and marked as completed")
                    else:
                        self.db.update_auto_order_status(order['id'], 'failed')
                        print(f"❌ Order #{order['id']} failed and marked as failed")
                    
                    
                    outcome = 'yes' if 'YES' in trigger_type else 'no'
                    self.price_monitor.reset_initial_price(market_alias, outcome)
                
            except Exception as e:
                print(f"❌ Error processing order #{order['id']}: {e}")
                import traceback
                traceback.print_exc()
    
    async def run(self):
        """Главный цикл worker'а"""
        print("🚀 Auto-Trade Worker started!")
        print(f"⏰ Check interval: {self.check_interval} seconds")
        print(f"📊 Monitoring prices and auto-orders...\n")
        
        iteration = 0
        
        while True:
            try:
                iteration += 1
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                print(f"[{timestamp}] Iteration #{iteration}")
                
                
                await self.check_and_execute_orders()
                
                
                await asyncio.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                print("\n⏹️ Worker stopped by user")
                break
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                import traceback
                traceback.print_exc()
                
                
                await asyncio.sleep(self.check_interval)


async def main():
    """worker'а"""
    
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    
    if not telegram_token:
        print("❌ TELEGRAM_TOKEN not found in environment!")
        return
    
    
    worker = AutoTradeWorker(telegram_token)
    await worker.run()


if __name__ == "__main__":
    print("="*60)
    print("🤖 OpiPoliX Auto-Trade Worker")
    print("="*60)
    
   
    asyncio.run(main())
