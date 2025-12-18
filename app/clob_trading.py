"""
CLOB Trading для OpiPoliX бота
Размещение ордеров через Polymarket CLOB API
"""
import os
from typing import Dict, Literal
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType, MarketOrderArgs
from py_builder_signing_sdk.config import BuilderConfig, RemoteBuilderConfig
from dotenv import load_dotenv

load_dotenv()

# Configuration
CLOB_URL = "https://clob.polymarket.com"
CHAIN_ID = 137  # Polygon Mainnet
BUILDER_SIGNING_URL = os.environ.get("BUILDER_SIGNING_URL")

# Local builder credentials (fallback)
BUILDER_API_KEY = os.environ.get("BUILDER_API_KEY")
BUILDER_SECRET = os.environ.get("BUILDER_SECRET")
BUILDER_PASS_PHRASE = os.environ.get("BUILDER_PASS_PHRASE")


class UserClobClient:
    """CLOB client для одного пользователя (как в твоём JS коде)"""
    
    def __init__(self, user_private_key: str, telegram_id: int = None):
        """
        Args:
            user_private_key: Расшифрованный приватный ключ пользователя
            telegram_id: ID пользователя для логирования
        """
        self.telegram_id = telegram_id
        self.private_key = user_private_key
        
        # Builder config для CLOB (REMOTE SIGNING!)
        if BUILDER_SIGNING_URL:
            print("🔐 Using REMOTE builder signing for CLOB")
            remote_config = RemoteBuilderConfig(url=BUILDER_SIGNING_URL)
            builder_config = BuilderConfig(remote_builder_config=remote_config)
        elif BUILDER_API_KEY and BUILDER_SECRET and BUILDER_PASS_PHRASE:
            print("🔑 Using LOCAL builder credentials for CLOB")
            from py_builder_signing_sdk.config import BuilderApiKeyCreds
            builder_config = BuilderConfig(
                local_builder_creds=BuilderApiKeyCreds(
                    key=BUILDER_API_KEY,
                    secret=BUILDER_SECRET,
                    passphrase=BUILDER_PASS_PHRASE
                )
            )
        else:
            raise ValueError("Builder credentials not configured!")
        
        # Initialize CLOB client (как в примере place_builder_order.py)
        # Документация: https://docs.polymarket.com/api-reference/builder-methods
        
        # Создаём temporary client для API credentials
        temp_client = ClobClient(
            host=CLOB_URL,
            key=self.private_key,
            chain_id=CHAIN_ID
        )
        
        print("🔑 Deriving API credentials...")
        api_creds = temp_client.create_or_derive_api_creds()
        
        # Теперь создаём основной client с credentials И builder config
        self.client = ClobClient(
            host=CLOB_URL,
            key=self.private_key,
            chain_id=CHAIN_ID,
            creds=api_creds,  # API credentials
            builder_config=builder_config  # Builder атрибуция!
        )
        
        print("✅ CLOB client initialized with builder attribution!")
    
    def create_market_order(
        self,
        token_id: str,
        side: Literal["BUY", "SELL"],
        amount_usdc: float
    ) -> Dict:
        """
        Создать market order (как в твоём JS коде)
        
        Args:
            token_id: ID токена (YES или NO)
            side: "BUY" или "SELL"
            amount_usdc: Сумма в USDC для покупки
        
        Returns:
            dict: {
                'order_id': str,
                'status': 'success' | 'failed' | 'error',
                'error': str (if error)
            }
        """
        try:
            print(f"📊 Creating {side} order: ${amount_usdc} for token {token_id[:16]}...")
            
            # Market Order - просто передаём amount в USDC!
            # Не нужно получать orderbook и считать size!
            order_args = MarketOrderArgs(
                token_id=token_id,
                amount=amount_usdc,  # Сумма в USDC
                side=side  # "BUY" или "SELL"
            )
            
            print(f"💡 Market order: ${amount_usdc} USDC")
            
            # Создаём market order
            signed_order = self.client.create_market_order(order_args)
            
            print(f"✅ Order created: {signed_order}")
            
            # Размещаем order
            response = self.client.post_order(signed_order, OrderType.FOK)  # Fill-Or-Kill
            
            print(f"✅ Order posted: {response}")
            
            return {
                'order_id': response.orderID if hasattr(response, 'orderID') else str(response),
                'amount': amount_usdc,
                'status': 'success'
            }
            
        except Exception as e:
            print(f"❌ Error creating order: {e}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_market_price(self, token_id: str, side: Literal["BUY", "SELL"]) -> float:
        """
        Получить текущую рыночную цену
        
        Args:
            token_id: ID токена
            side: "BUY" или "SELL"
        
        Returns:
            float: Цена или 0.0 если ошибка
        """
        try:
            orderbook = self.client.get_order_book(token_id)
            
            if side == "BUY":
                if orderbook.asks:
                    return float(orderbook.asks[0].price)
            else:  # SELL
                if orderbook.bids:
                    return float(orderbook.bids[0].price)
            
            return 0.0
            
        except Exception as e:
            print(f"❌ Error getting price: {e}")
            return 0.0


def trade_market(
    user_private_key: str,
    token_id: str,
    side: Literal["BUY", "SELL"],
    amount_usdc: float,
    telegram_id: int = None
) -> Dict:
    """
    Helper function для размещения market order
    
    Args:
        user_private_key: Расшифрованный приватный ключ
        token_id: ID токена (YES или NO)
        side: "BUY" или "SELL"
        amount_usdc: Сумма в USDC
        telegram_id: ID пользователя
    
    Returns:
        dict: Результат ордера
    """
    client = UserClobClient(user_private_key, telegram_id)
    return client.create_market_order(token_id, side, amount_usdc)
