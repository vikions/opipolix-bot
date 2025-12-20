"""
Balance Checker для OpiPoliX бота
Проверка балансов USDC и позиций на маркетах
"""
import os
from typing import Dict
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

# Polygon RPC
POLYGON_RPC = os.environ.get("POLYGON_RPC", "https://polygon-rpc.com")

# Contract addresses (Polygon Mainnet)
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
CTF_ADDRESS = "0x4d97dcd97ec945f40cf65f87097ace5ea0476045"

# Market Token IDs
MARKET_TOKENS = {
    "metamask": {
        "yes": "101163575689611177694586697172798294092987709960375574777760542313937687808591",
        "no": "102949690272049881918816161009598998660276278148863115139226223419430092123884"
    },
    "base": {
        "yes": "TBD",  
        "no": "TBD"
    }
}


class BalanceChecker:
    
    
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
        
        
        self.usdc_abi = [{
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        }]
        
        
        self.ctf_abi = [{
            "constant": True,
            "inputs": [
                {"name": "_owner", "type": "address"},
                {"name": "_id", "type": "uint256"}
            ],
            "name": "balanceOf",
            "outputs": [{"name": "", "type": "uint256"}],
            "type": "function"
        }]
        
        self.usdc_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ADDRESS),
            abi=self.usdc_abi
        )
        
        self.ctf_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(CTF_ADDRESS),
            abi=self.ctf_abi
        )
    
    def get_usdc_balance(self, address: str) -> float:
       
        try:
            checksum_address = Web3.to_checksum_address(address)
            balance_wei = self.usdc_contract.functions.balanceOf(checksum_address).call()
            
            balance_usdc = balance_wei / 1e6
            return balance_usdc
        except Exception as e:
            print(f"Error getting USDC balance: {e}")
            return 0.0
    
    def get_position_balance(self, address: str, token_id: str) -> float:
       
        try:
            checksum_address = Web3.to_checksum_address(address)
            balance = self.ctf_contract.functions.balanceOf(
                checksum_address,
                int(token_id)
            ).call()
            return float(balance)
        except Exception as e:
            print(f"Error getting position balance: {e}")
            return 0.0
    
    def get_full_balance(self, eoa_address: str, safe_address: str = None) -> Dict:
        
        print(f"🔍 Checking balance for EOA: {eoa_address}")
        
        # USDC balances
        eoa_usdc = self.get_usdc_balance(eoa_address)
        safe_usdc = 0.0
        
        if safe_address:
            print(f"🔍 Checking balance for Safe: {safe_address}")
            safe_usdc = self.get_usdc_balance(safe_address)
        
        total_usdc = eoa_usdc + safe_usdc
        
        # Positions 
        positions = {
            'metamask': {'yes': 0.0, 'no': 0.0},
            'base': {'yes': 0.0, 'no': 0.0}
        }
        
        if safe_address:
            # MetaMask positions
            if MARKET_TOKENS['metamask']['yes'] != 'TBD':
                positions['metamask']['yes'] = self.get_position_balance(
                    safe_address, 
                    MARKET_TOKENS['metamask']['yes']
                )
                positions['metamask']['no'] = self.get_position_balance(
                    safe_address,
                    MARKET_TOKENS['metamask']['no']
                )
            
            # Base positions 
            if MARKET_TOKENS['base']['yes'] != 'TBD':
                positions['base']['yes'] = self.get_position_balance(
                    safe_address,
                    MARKET_TOKENS['base']['yes']
                )
                positions['base']['no'] = self.get_position_balance(
                    safe_address,
                    MARKET_TOKENS['base']['no']
                )
        
        return {
            'eoa_usdc': eoa_usdc,
            'safe_usdc': safe_usdc,
            'total_usdc': total_usdc,
            'positions': positions
        }


def format_balance_message(balance: Dict) -> str:
    
    lines = ["💰 *Your Balance*\n"]
    
    # USDC balance 
    lines.append("*USDC:*")
    lines.append(f"  ${balance['safe_usdc']:.2f}\n")
    
    # Positions
    positions = balance['positions']
    has_positions = False
    
    lines.append("*Positions:*")
    
    # MetaMask
    mm_yes = positions['metamask']['yes']
    mm_no = positions['metamask']['no']
    if mm_yes > 0 or mm_no > 0:
        has_positions = True
        lines.append("  MetaMask:")
        if mm_yes > 0:
            lines.append(f"    YES: {mm_yes:.2f} shares")
        if mm_no > 0:
            lines.append(f"    NO: {mm_no:.2f} shares")
    
    # Base
    base_yes = positions['base']['yes']
    base_no = positions['base']['no']
    if base_yes > 0 or base_no > 0:
        has_positions = True
        lines.append("  Base:")
        if base_yes > 0:
            lines.append(f"    YES: {base_yes:.2f} shares")
        if base_no > 0:
            lines.append(f"    NO: {base_no:.2f} shares")
    
    if not has_positions:
        lines.append("  No positions yet")
    
    return "\n".join(lines)


# Helper function
def check_user_balance(eoa_address: str, safe_address: str = None) -> str:
  
    checker = BalanceChecker()
    balance = checker.get_full_balance(eoa_address, safe_address)
    return format_balance_message(balance)
