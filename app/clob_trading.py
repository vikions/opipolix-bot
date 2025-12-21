
import os
from typing import Dict, Literal, Optional
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderType, MarketOrderArgs
from py_builder_signing_sdk.config import BuilderConfig, RemoteBuilderConfig
from dotenv import load_dotenv

load_dotenv()


CLOB_URL = "https://clob.polymarket.com"
CHAIN_ID = 137  
BUILDER_SIGNING_URL = os.environ.get("BUILDER_SIGNING_URL")


BUILDER_API_KEY = os.environ.get("BUILDER_API_KEY")
BUILDER_SECRET = os.environ.get("BUILDER_SECRET")
BUILDER_PASS_PHRASE = os.environ.get("BUILDER_PASS_PHRASE")


class UserClobClient:
    

    def __init__(
        self,
        user_private_key: str,
        telegram_id: int = None,
        funder_address: Optional[str] = None,  # <-- SAFE / proxy address
    ):
        """
        Args:
            user_private_key: 
            telegram_id: 
            funder_address: 
        """
        self.telegram_id = telegram_id
        self.private_key = user_private_key
        self.funder_address = funder_address

        
        if BUILDER_API_KEY and BUILDER_SECRET and BUILDER_PASS_PHRASE:
            print("🔑 Using LOCAL builder credentials for CLOB")
            from py_builder_signing_sdk.config import BuilderApiKeyCreds

            builder_config = BuilderConfig(
                local_builder_creds=BuilderApiKeyCreds(
                    key=BUILDER_API_KEY,
                    secret=BUILDER_SECRET,
                    passphrase=BUILDER_PASS_PHRASE,
                )
            )
        elif BUILDER_SIGNING_URL:
            print("🔐 Using REMOTE builder signing for CLOB")
            remote_config = RemoteBuilderConfig(url=BUILDER_SIGNING_URL)
            builder_config = BuilderConfig(remote_builder_config=remote_config)
        else:
            raise ValueError("Builder credentials not configured!")

       
        signature_type = 2 if self.funder_address else 0

      
        self.client = ClobClient(
            host=CLOB_URL,
            key=self.private_key,
            chain_id=CHAIN_ID,
            signature_type=signature_type,
            funder=self.funder_address,
            builder_config=builder_config,
        )

        print("🔑 Deriving API credentials...")
        self.client.set_api_creds(self.client.create_or_derive_api_creds())

        if self.funder_address:
            print(f"✅ CLOB client initialized with funder: {self.funder_address} (signature_type={signature_type})")
        else:
            print(f"✅ CLOB client initialized without funder (EOA mode, signature_type={signature_type})")

    def create_market_order(
        self,
        token_id: str,
        side: Literal["BUY", "SELL"],
        amount_usdc: float,
    ) -> Dict:
        try:
            print(f"📊 Creating {side} order: ${amount_usdc} for token {token_id[:16]}...")
            order_args = MarketOrderArgs(
                token_id=token_id,
                amount=amount_usdc,
                side=side,
            )

            print(f"💡 Market order: ${amount_usdc} USDC")

            signed_order = self.client.create_market_order(order_args)
            print(f"✅ Order created: {signed_order}")

            response = self.client.post_order(signed_order, OrderType.FOK)
            print(f"✅ Order posted: {response}")

            # Extract order ID properly
            order_id = None
            if hasattr(response, 'orderID'):
                order_id = response.orderID
            elif hasattr(response, 'order_id'):
                order_id = response.order_id
            elif isinstance(response, dict):
                order_id = response.get('orderID') or response.get('order_id')
            else:
                order_id = str(response)

            return {
                "order_id": order_id,
                "amount": amount_usdc,
                "status": "success",
            }

        except Exception as e:
            print(f"❌ Error creating order: {e}")
            import traceback

            traceback.print_exc()
            return {"status": "error", "error": str(e)}

    def get_market_price(self, token_id: str, side: Literal["BUY", "SELL"]) -> float:
        try:
            orderbook = self.client.get_order_book(token_id)

            if side == "BUY":
                if orderbook.asks:
                    return float(orderbook.asks[0].price)
            else:
                if orderbook.bids:
                    return float(orderbook.bids[0].price)

            return 0.0

        except Exception as e:
            print(f"❌ Error getting price: {e}")
            return 0.0

    def get_token_balance(self, token_id: str) -> float:
        """
        
        
        Returns:
            float: 
        """
        try:
           
            positions_response = self.client.get_positions()
            
            if not positions_response:
                print(f"⚠️ No positions found")
                return 0.0
            
            
            positions = []
            if isinstance(positions_response, list):
                positions = positions_response
            elif hasattr(positions_response, 'data'):
                positions = positions_response.data
            elif hasattr(positions_response, 'positions'):
                positions = positions_response.positions
            
            
            for position in positions:
                
                pos_token_id = None
                if hasattr(position, 'asset_id'):
                    pos_token_id = position.asset_id
                elif hasattr(position, 'token_id'):
                    pos_token_id = position.token_id
                elif isinstance(position, dict):
                    pos_token_id = position.get('asset_id') or position.get('token_id')
                
                if pos_token_id == token_id:
                    
                    balance = 0.0
                    if hasattr(position, 'balance'):
                        balance = float(position.balance)
                    elif hasattr(position, 'size'):
                        balance = float(position.size)
                    elif isinstance(position, dict):
                        balance = float(position.get('balance', 0) or position.get('size', 0))
                    
                    print(f"✅ Found token balance: {balance}")
                    return balance
            
            print(f"⚠️ Token {token_id[:16]} not found in positions")
            return 0.0
            
        except Exception as e:
            print(f"❌ Error getting balance for token {token_id[:16]}: {e}")
            import traceback
            traceback.print_exc()
            return 0.0


def trade_market(
    user_private_key: str,
    token_id: str,
    side: Literal["BUY", "SELL"],
    amount_usdc: float,
    telegram_id: int = None,
    funder_address: Optional[str] = None,  # <-- добавили
) -> Dict:
    """
    Helper function 

    funder_address: 
    """
    client = UserClobClient(user_private_key, telegram_id, funder_address=funder_address)
    return client.create_market_order(token_id, side, amount_usdc)


def get_token_balance(
    user_private_key: str,
    token_id: str,
    funder_address: str,
    telegram_id: int = None,
) -> float:
    """
    
    
    Returns:
        float: 
    """
    client = UserClobClient(user_private_key, telegram_id, funder_address=funder_address)
    return client.get_token_balance(token_id)
