"""
Withdraw Manager для OpiPoliX бота
Вывод USDC из Safe через Relayer (GASLESS!)
"""
from typing import Dict
from eth_utils import keccak, to_checksum_address
from eth_abi import encode
from py_builder_relayer_client.models import OperationType, SafeTransaction
from relayer_client import UserRelayerClient

# Contract addresses
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"


def withdraw_usdc_from_safe(
    user_private_key: str,
    recipient_address: str,
    amount_usdc: float,
    telegram_id: int = None
) -> Dict:
    """
    Вывести USDC из Safe на указанный адрес (GASLESS!)
    
    Args:
        user_private_key: Расшифрованный приватный ключ пользователя
        recipient_address: Адрес получателя (EOA или другой)
        amount_usdc: Сумма в USDC (например 10.5)
        telegram_id: ID пользователя для логирования
    
    Returns:
        dict: {
            'tx_hash': str,
            'status': 'success' | 'failed' | 'error',
            'error': str (if error)
        }
    """
    try:
        print(f"💸 Withdrawing {amount_usdc} USDC for user {telegram_id}...")
        
        # Создаём Relayer client
        relayer = UserRelayerClient(user_private_key, telegram_id)
        
        # Конвертируем amount в wei (USDC has 6 decimals)
        amount_wei = int(amount_usdc * 1e6)
        
        # Создаём transfer function call data
        def _function_selector(signature: str) -> bytes:
            return keccak(text=signature)[:4]
        
        selector = _function_selector("transfer(address,uint256)")
        encoded_args = encode(
            ["address", "uint256"],
            [to_checksum_address(recipient_address), amount_wei]
        )
        transfer_data = "0x" + (selector + encoded_args).hex()
        
        # Создаём SafeTransaction
        safe_tx = SafeTransaction(
            to=to_checksum_address(USDC_ADDRESS),
            operation=OperationType.Call,
            data=transfer_data,
            value="0"
        )
        
        # Выполняем через Relayer (gasless!)
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
