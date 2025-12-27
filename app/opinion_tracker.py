"""
Opinion Position Tracker
Track user positions on Opinion markets
"""
import os
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

from opinion_clob_sdk import Client

OPINION_API_KEY = os.getenv('API_KEY')
OPINION_HOST = os.getenv('HOST', 'https://proxy.opinion.trade:8443')
BNB_CHAIN_ID = 56
BNB_RPC_URL = 'https://bsc.nodereal.io'


def get_user_positions(user_address: str) -> Dict:
    """
    Get user's positions on Opinion
    
    Args:
        user_address: User's wallet address
        
    Returns:
        Dict with positions data
    """
    try:
        # Create read-only client with user's address
        client = Client(
            host=OPINION_HOST,
            apikey=OPINION_API_KEY,  # Our API key
            chain_id=BNB_CHAIN_ID,
            rpc_url='',  # Not needed for read-only
            private_key='0x0000000000000000000000000000000000000000000000000000000000000001',  # Dummy
            multi_sig_addr=user_address  # User's address!
        )
        
        # Get positions
        positions_response = client.get_my_positions()
        
        if positions_response.errno != 0:
            return {
                'status': 'error',
                'error': positions_response.errmsg
            }
        
        positions = positions_response.result if hasattr(positions_response, 'result') else []
        
        return {
            'status': 'success',
            'positions': positions,
            'address': user_address
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


def get_user_balances(user_address: str) -> Dict:
    """
    Get user's token balances on Opinion + USDT on-chain
    
    Args:
        user_address: User's wallet address
        
    Returns:
        Dict with balances data
    """
    try:
        # Create read-only client
        client = Client(
            host=OPINION_HOST,
            apikey=OPINION_API_KEY,
            chain_id=BNB_CHAIN_ID,
            rpc_url='',
            private_key='0x0000000000000000000000000000000000000000000000000000000000000001',
            multi_sig_addr=user_address
        )
        
        # Get balances from Opinion API
        balances_response = client.get_my_balances()
        
        if balances_response.errno != 0:
            return {
                'status': 'error',
                'error': balances_response.errmsg
            }
        
        balances = balances_response.result if hasattr(balances_response, 'result') else []
        
        # Also get USDT balance on-chain
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider('https://bsc.nodereal.io'))
        
        USDT_ADDRESS = "0x55d398326f99059fF775485246999027B3197955"
        usdt_abi = [{
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        }]
        
        usdt_contract = w3.eth.contract(
            address=Web3.to_checksum_address(USDT_ADDRESS),
            abi=usdt_abi
        )
        
        usdt_balance_wei = usdt_contract.functions.balanceOf(
            Web3.to_checksum_address(user_address)
        ).call()
        
        usdt_balance = usdt_balance_wei / 10**18
        
        return {
            'status': 'success',
            'balances': balances,
            'usdt_balance': usdt_balance,
            'address': user_address
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


def get_user_trades(user_address: str, limit: int = 10) -> Dict:
    """
    Get user's recent trades on Opinion
    
    Args:
        user_address: User's wallet address
        limit: Number of trades to fetch
        
    Returns:
        Dict with trades data
    """
    try:
        client = Client(
            host=OPINION_HOST,
            apikey=OPINION_API_KEY,
            chain_id=BNB_CHAIN_ID,
            rpc_url='',
            private_key='0x0000000000000000000000000000000000000000000000000000000000000001',
            multi_sig_addr=user_address
        )
        
        # Get trades
        trades_response = client.get_my_trades(limit=limit)
        
        if trades_response.errno != 0:
            return {
                'status': 'error',
                'error': trades_response.errmsg
            }
        
        trades = trades_response.result if hasattr(trades_response, 'result') else []
        
        return {
            'status': 'success',
            'trades': trades,
            'address': user_address
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


def format_positions_message(positions_data: Dict) -> str:
    """
    Format positions into readable message
    
    Args:
        positions_data: Result from get_user_positions()
        
    Returns:
        Formatted message string
    """
    if positions_data['status'] != 'success':
        return f"❌ Error: {positions_data.get('error', 'Unknown')}"
    
    # Get positions from result
    result = positions_data.get('positions')
    address = positions_data.get('address', 'Unknown')
    
    # Handle different response types
    if hasattr(result, 'data'):
        positions = result.data if result.data else []
    elif isinstance(result, list):
        positions = result
    else:
        positions = []
    
    if not positions or len(positions) == 0:
        return (
            f"💼 *Opinion Positions*\n\n"
            f"Address: `{address[:10]}...{address[-8:]}`\n\n"
            f"📊 No open positions"
        )
    
    message = f"💼 *Opinion Positions*\n\n"
    message += f"Address: `{address[:10]}...{address[-8:]}`\n\n"
    
    total_value = 0
    
    for idx, pos in enumerate(positions):
        # Extract position data (handle dict or object)
        if hasattr(pos, 'market_id'):
            market_id = pos.market_id
            token_id = pos.token_id if hasattr(pos, 'token_id') else 'Unknown'
            amount = pos.amount if hasattr(pos, 'amount') else 0
        else:
            market_id = pos.get('marketId', 'Unknown')
            token_id = pos.get('tokenId', 'Unknown')
            amount = pos.get('amount', 0)
        
        # Try to get market info
        market_name = f"Market #{market_id}"
        
        # Format amount (18 decimals)
        if isinstance(amount, (int, float)):
            amount_formatted = amount / 10**18
        else:
            amount_formatted = 0
        
        message += f"📊 *Position {idx + 1}*\n"
        message += f"   Market: {market_name}\n"
        message += f"   Amount: {amount_formatted:.4f} tokens\n\n"
        
        total_value += amount_formatted
    
    message += f"💰 *Total Positions:* {len(positions)}\n"
    
    return message


def format_balances_message(balances_data: Dict) -> str:
    """
    Format balances into readable message
    """
    if balances_data['status'] != 'success':
        return f"❌ Error: {balances_data.get('error', 'Unknown')}"
    
    result = balances_data.get('balances')
    address = balances_data.get('address', 'Unknown')
    usdt_balance = balances_data.get('usdt_balance', 0)
    
    # Handle different response types
    if hasattr(result, 'data'):
        balances = result.data if result.data else []
    elif isinstance(result, list):
        balances = result
    else:
        balances = []
    
    message = f"💰 *Opinion Balances*\n\n"
    message += f"Address: `{address[:10]}...{address[-8:]}`\n\n"
    
    # Show USDT balance
    message += f"💵 *USDT:* {usdt_balance:.2f} USDT\n\n"
    
    # Show outcome tokens
    if not balances or len(balances) == 0:
        message += f"📊 No outcome token positions"
    else:
        message += "*Outcome Tokens:*\n"
        for idx, bal in enumerate(balances):
            # Handle dict or object
            if hasattr(bal, 'token_id'):
                token_id = bal.token_id
                amount = bal.amount if hasattr(bal, 'amount') else 0
            else:
                token_id = bal.get('tokenId', 'Unknown')
                amount = bal.get('amount', 0)
            
            if isinstance(amount, (int, float)):
                amount_formatted = amount / 10**18
            else:
                amount_formatted = 0
            
            if amount_formatted > 0:
                message += f"📈 Token {idx + 1}: {amount_formatted:.4f}\n"
    
    return message
