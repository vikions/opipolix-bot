"""
Cashback payments via Safe wallet
"""
from web3 import Web3
from eth_account import Account
import os


POLYGON_RPC = os.environ.get("POLYGON_RPC", "https://polygon-rpc.com")
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"

# Your personal wallet to send cashback FROM
CASHBACK_WALLET_KEY = os.environ.get("CASHBACK_WALLET_KEY")  # Add to .env


USDC_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]


def send_cashback(recipient_address: str, amount_usdc: float) -> dict:
    """
    Send USDC cashback to user's Safe
    
    Args:
        recipient_address: User's Safe address
        amount_usdc: Amount in USDC (e.g., 1.0)
    
    Returns:
        {'status': 'success', 'tx_hash': '0x...'} or {'status': 'error', 'error': '...'}
    """
    
    if not CASHBACK_WALLET_KEY:
        return {
            'status': 'error',
            'error': 'CASHBACK_WALLET_KEY not configured'
        }
    
    try:
        w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
        
        # Your wallet
        cashback_account = Account.from_key(CASHBACK_WALLET_KEY)
        
        # USDC contract
        usdc_contract = w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ADDRESS),
            abi=USDC_ABI
        )
        
        # Amount in USDC (6 decimals)
        amount_raw = int(amount_usdc * 1e6)
        
        # Build transaction
        tx = usdc_contract.functions.transfer(
            Web3.to_checksum_address(recipient_address),
            amount_raw
        ).build_transaction({
            'from': cashback_account.address,
            'gas': 100000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(cashback_account.address),
            'chainId': 137  # Polygon
        })
        
        # Sign and send
        signed = cashback_account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        
        # Wait for confirmation
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt.status == 1:
            return {
                'status': 'success',
                'tx_hash': tx_hash.hex()
            }
        else:
            return {
                'status': 'error',
                'error': 'Transaction failed'
            }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }
