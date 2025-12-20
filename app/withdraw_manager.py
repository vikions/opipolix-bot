
from typing import Dict
from eth_utils import keccak, to_checksum_address
from eth_abi import encode
from py_builder_relayer_client.models import OperationType, SafeTransaction
from relayer_client import UserRelayerClient


USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"


def withdraw_usdc_from_safe(
    user_private_key: str,
    recipient_address: str,
    amount_usdc: float,
    telegram_id: int = None
) -> Dict:
   
    try:
        print(f"💸 Withdrawing {amount_usdc} USDC for user {telegram_id}...")
        
       
        relayer = UserRelayerClient(user_private_key, telegram_id)
        
       
        amount_wei = int(amount_usdc * 1e6)
        
        
        def _function_selector(signature: str) -> bytes:
            return keccak(text=signature)[:4]
        
        selector = _function_selector("transfer(address,uint256)")
        encoded_args = encode(
            ["address", "uint256"],
            [to_checksum_address(recipient_address), amount_wei]
        )
        transfer_data = "0x" + (selector + encoded_args).hex()
        
        
        safe_tx = SafeTransaction(
            to=to_checksum_address(USDC_ADDRESS),
            operation=OperationType.Call,
            data=transfer_data,
            value="0"
        )
        
        
        response = relayer.client.execute(
            [safe_tx],
            metadata=f"USDC withdraw {amount_usdc} for TG user {telegram_id}"
        )
        
        result = response.wait()
        
        if result:
            tx_hash = result.get('transactionHash') or result.get('transaction_hash')
            print(f"✅ USDC withdrawn: {tx_hash}")
            return {
                'tx_hash': tx_hash,
                'status': 'success'
            }
        else:
            return {
                'status': 'failed',
                'error': 'Transaction failed'
            }
            
    except Exception as e:
        print(f"❌ Error withdrawing USDC: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }
