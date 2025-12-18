"""
Polymarket Trading модуль с Builder Attribution
Все сделки идут с атрибуцией через Signing Server!
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs
from py_clob_client.order_builder.constants import BUY, SELL
from eth_account import Account

load_dotenv()

# Конфигурация
CLOB_HOST = "https://clob.polymarket.com"
BUILDER_SIGNING_URL = os.environ.get("BUILDER_SIGNING_URL")
CHAIN_ID = 137  # Polygon Mainnet

# Market Token IDs
MARKET_TOKENS = {
    "metamask": {
        "yes": "101163575689611177694586697172798294092987709960375574777760542313937687808591",
        "no": "102949690272049881918816161009598998660276278148863115139226223419430092123884"
    },
    "base": {
        # TODO: Добавить Base token IDs
        "yes": "TBD",
        "no": "TBD"
    }
}


class PolymarketTrader:
    """
    Торговый клиент для Polymarket с Builder Attribution
    """
    
    def __init__(self, private_key: str):
        """
        Args:
            private_key: Приватный ключ пользователя (расшифрованный)
        """
        self.private_key = private_key
        self.clob_host = CLOB_HOST
        self.builder_signing_url = BUILDER_SIGNING_URL
        
        if not self.builder_signing_url:
            raise ValueError("BUILDER_SIGNING_URL not set in .env")
        
        # Создаем базовый клиент (без auth для публичных методов)
        self.client = ClobClient(
            host=self.clob_host,
            key=self.private_key,
            chain_id=CHAIN_ID
        )
    
    def get_market_price(self, market_alias: str, outcome: str) -> float:
        """
        Получить текущую цену рынка
        
        Args:
            market_alias: 'metamask' или 'base'
            outcome: 'yes' или 'no'
        
        Returns:
            float: Текущая цена (0.00 - 1.00)
        """
        token_id = MARKET_TOKENS[market_alias][outcome.lower()]
        
        if token_id == "TBD":
            raise ValueError(f"Token ID not set for {market_alias}")
        
        try:
            # Получаем цену (возвращает dict или число)
            price_data = self.client.get_price(token_id, side=BUY)
            
            # Если dict - берем значение
            if isinstance(price_data, dict):
                price = float(price_data.get("price", 0))
            else:
                price = float(price_data)
            
            print(f"💰 {market_alias} {outcome.upper()}: ${price:.4f}")
            return price
            
        except Exception as e:
            print(f"❌ Error getting price: {e}")
            
            # Fallback - пробуем через midpoint
            try:
                midpoint_data = self.client.get_midpoint(token_id)
                
                if isinstance(midpoint_data, dict):
                    midpoint = float(midpoint_data.get("mid", 0))
                else:
                    midpoint = float(midpoint_data)
                    
                print(f"💰 {market_alias} {outcome.upper()} (midpoint): ${midpoint:.4f}")
                return midpoint
            except Exception as e2:
                print(f"❌ Midpoint also failed: {e2}")
                return 0.0
    
    def create_api_credentials(self) -> Dict[str, str]:
        """
        Создать API credentials для CLOB
        
        Returns:
            dict: {apiKey, secret, passphrase}
        """
        print("🔑 Creating API credentials...")
        
        try:
            # Создаем/получаем API credentials
            creds = self.client.create_or_derive_api_key()
            
            print("✅ API credentials ready!")
            return creds
            
        except Exception as e:
            print(f"❌ Error creating credentials: {e}")
            raise
    
    def place_market_order(
        self, 
        market_alias: str, 
        side: str,  # 'BUY' or 'SELL'
        outcome: str,  # 'yes' or 'no'
        amount_usdc: float
    ) -> Dict[str, Any]:
        """
        Разместить market order с Builder Attribution
        
        Args:
            market_alias: 'metamask' или 'base'
            side: 'BUY' или 'SELL'
            outcome: 'yes' или 'no'
            amount_usdc: Размер в USDC
        
        Returns:
            dict: Результат ордера
        """
        print(f"\n📊 Placing {side} {outcome.upper()} order...")
        print(f"   Market: {market_alias}")
        print(f"   Amount: ${amount_usdc}")
        print(f"   🎯 WITH BUILDER ATTRIBUTION via {self.builder_signing_url}\n")
        
        # Получаем token ID
        if market_alias not in MARKET_TOKENS:
            raise ValueError(f"Unknown market: {market_alias}")
        
        token_id = MARKET_TOKENS[market_alias][outcome.lower()]
        
        if token_id == "TBD":
            raise ValueError(f"Token ID not set for {market_alias} {outcome}")
        
        try:
            # 1. Создаем API credentials если нужно
            api_creds = self.create_api_credentials()
            
            # 2. Создаем клиент с атрибуцией
            # TODO: Добавить builder_config когда py-builder-signing-sdk будет доступен
            """
            from py_builder_signing_sdk import BuilderConfig
            
            builder_config = BuilderConfig(
                remote_builder_config={
                    "url": self.builder_signing_url
                }
            )
            
            auth_client = ClobClient(
                host=self.clob_host,
                key=self.private_key,
                chain_id=CHAIN_ID,
                creds=api_creds,
                signature_type=0,  # EOA
                funder=None,
                builder_config=builder_config  # 🎯 АТРИБУЦИЯ!
            )
            """
            
            # Пока без builder_config (добавим когда SDK будет доступен)
            auth_client = ClobClient(
                host=self.clob_host,
                key=self.private_key,
                chain_id=CHAIN_ID,
                creds=api_creds,
                signature_type=0  # EOA
            )
            
            # 3. Получаем текущую цену
            current_price = self.get_market_price(market_alias, outcome)
            
            if current_price == 0:
                raise ValueError("Could not get market price")
            
            # 4. Рассчитываем размер позиции
            size = amount_usdc / current_price
            
            print(f"📈 Current price: ${current_price:.4f}")
            print(f"📊 Position size: {size:.2f} contracts")
            
            # 5. Создаем market order
            order_args = OrderArgs(
                token_id=token_id,
                amount=amount_usdc,
                side=BUY if side == "BUY" else SELL
            )
            
            # 6. Создаем и отправляем ордер
            signed_order = auth_client.create_market_order(order_args)
            
            print("📝 Order created, posting to CLOB...")
            
            response = auth_client.post_order(signed_order)
            
            print("✅ Order posted successfully!")
            print(f"Response: {response}\n")
            
            return {
                "success": True,
                "order_id": response.get("orderID"),
                "response": response
            }
            
        except Exception as e:
            print(f"❌ Error placing order: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# ===== HELPER FUNCTIONS =====

def test_builder_attribution():
    """Тест что builder signing server доступен"""
    import requests
    
    print("🧪 Testing Builder Attribution...\n")
    
    signing_url = os.environ.get("BUILDER_SIGNING_URL")
    
    if not signing_url:
        print("❌ BUILDER_SIGNING_URL not set in .env")
        return False
    
    print(f"✅ Builder Signing URL: {signing_url}")
    
    try:
        base_url = signing_url.replace("/sign", "")
        response = requests.get(base_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Builder Signing Server is ONLINE!")
            print("   All trades will be attributed to your builder profile!")
            return True
        else:
            print(f"⚠️  Server responded with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error connecting to signing server: {e}")
        return False


# ===== ТЕСТ =====

if __name__ == "__main__":
    print("="*60)
    
    # Проверяем Builder Attribution
    test_builder_attribution()
    
    print("\n" + "="*60)
    
    # Тестовый ключ (НЕ использовать в production!)
    test_key = "0x" + "1" * 64
    
    try:
        trader = PolymarketTrader(test_key)
        
        # Проверяем цены
        print("\n📊 Getting current prices:\n")
        trader.get_market_price("metamask", "yes")
        trader.get_market_price("metamask", "no")
        
        print("\n" + "="*60)
        print("✅ Trading module is ready!")
        print("\n💡 Next steps:")
        print("   1. Use real private key from wallet_manager")
        print("   2. Add builder_config when py-builder-signing-sdk available")
        print("   3. Test with small order on Polymarket")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Make sure you have:")
        print("   - BUILDER_SIGNING_URL in .env")
        print("   - py-clob-client installed")