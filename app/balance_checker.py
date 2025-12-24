"""
Balance Checker для OpiPoliX бота
Проверка балансов USDC и позиций на маркетах
"""
import os
from typing import Dict
from web3 import Web3
from dotenv import load_dotenv
import requests

load_dotenv()

# Polygon RPC
POLYGON_RPC = os.environ.get("POLYGON_RPC", "https://polygon-rpc.com")

# Contract addresses (Polygon Mainnet)
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
CTF_ADDRESS = "0x4d97dcd97ec945f40cf65f87097ace5ea0476045"

# Market Token IDs (updated to June 30 market)
MARKET_TOKENS = {
    "metamask": {
        "yes": "110325437323003864440364193681628128179433892752231328064623776035311134623682",
        "no": "77680902575693269510705775150133261883431641996305813878639196300490247886068"
    },
    "base": {
        "yes": "104771646709660831592727707032658923058293444911215259720234012315470229507167",
        "no": "91704486839398022652930625279905848372527977307744447009017770224967808697336"
    },
    "abstract": {
        "yes": "105292534464588119413823901919588224897612305776681795693919323419047416388812",
        "no": "98646985707839121837958202212263078387820716702786874164268337295747851893706"
    },
    "extended": {
        "yes": "80202018619101908013933944100239367385491528832020028327612486898619283802751",
        "no": "33249883623946882498042187494418816609278977641116912274628462290026666786835"
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
    
    def get_token_price(self, token_id: str) -> float:
        """Get current price of token from Polymarket CLOB API"""
        try:
            # Use CLOB API to get price
            response = requests.get(
                f"https://clob.polymarket.com/prices-history",
                params={
                    "interval": "1m",
                    "market": token_id,
                    "fidelity": 1
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    # Get latest price
                    latest = data[-1]
                    price = float(latest.get('price', 0))
                    return price
            
            # Fallback: try orderbook
            response = requests.get(
                f"https://clob.polymarket.com/book",
                params={"token_id": token_id},
                timeout=5
            )
            
            if response.status_code == 200:
                book = response.json()
                # Mid price = (best_bid + best_ask) / 2
                if book.get('bids') and book.get('asks'):
                    best_bid = float(book['bids'][0]['price']) if book['bids'] else 0
                    best_ask = float(book['asks'][0]['price']) if book['asks'] else 0
                    if best_bid > 0 and best_ask > 0:
                        return (best_bid + best_ask) / 2
            
            return 0.0
            
        except Exception as e:
            print(f"Error getting token price: {e}")
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
            'base': {'yes': 0.0, 'no': 0.0},
            'abstract': {'yes': 0.0, 'no': 0.0},
            'extended': {'yes': 0.0, 'no': 0.0}
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
            
            # Abstract positions
            if MARKET_TOKENS['abstract']['yes'] != 'TBD':
                positions['abstract']['yes'] = self.get_position_balance(
                    safe_address,
                    MARKET_TOKENS['abstract']['yes']
                )
                positions['abstract']['no'] = self.get_position_balance(
                    safe_address,
                    MARKET_TOKENS['abstract']['no']
                )
            
            # Extended positions
            if MARKET_TOKENS['extended']['yes'] != 'TBD':
                positions['extended']['yes'] = self.get_position_balance(
                    safe_address,
                    MARKET_TOKENS['extended']['yes']
                )
                positions['extended']['no'] = self.get_position_balance(
                    safe_address,
                    MARKET_TOKENS['extended']['no']
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
    
    # Get prices for calculation
    checker = BalanceChecker()
    
    lines.append("*Positions:*")
    
    # MetaMask
    mm_yes = positions['metamask']['yes']
    mm_no = positions['metamask']['no']
    if mm_yes > 0 or mm_no > 0:
        has_positions = True
        lines.append("  MetaMask:")
        if mm_yes > 0:
            # Convert raw balance to actual shares (divide by 1e6)
            shares = mm_yes / 1e6
            price = checker.get_token_price(MARKET_TOKENS['metamask']['yes'])
            usd_value = shares * price if price > 0 else 0
            if usd_value > 0:
                lines.append(f"    YES: {shares:.2f} shares (~${usd_value:.2f})")
            else:
                lines.append(f"    YES: {shares:.2f} shares")
        if mm_no > 0:
            shares = mm_no / 1e6
            price = checker.get_token_price(MARKET_TOKENS['metamask']['no'])
            usd_value = shares * price if price > 0 else 0
            if usd_value > 0:
                lines.append(f"    NO: {shares:.2f} shares (~${usd_value:.2f})")
            else:
                lines.append(f"    NO: {shares:.2f} shares")
    
    # Base
    base_yes = positions['base']['yes']
    base_no = positions['base']['no']
    if base_yes > 0 or base_no > 0:
        has_positions = True
        lines.append("  Base:")
        if base_yes > 0:
            shares = base_yes / 1e6
            price = checker.get_token_price(MARKET_TOKENS['base']['yes'])
            usd_value = shares * price if price > 0 else 0
            if usd_value > 0:
                lines.append(f"    YES: {shares:.2f} shares (~${usd_value:.2f})")
            else:
                lines.append(f"    YES: {shares:.2f} shares")
        if base_no > 0:
            shares = base_no / 1e6
            price = checker.get_token_price(MARKET_TOKENS['base']['no'])
            usd_value = shares * price if price > 0 else 0
            if usd_value > 0:
                lines.append(f"    NO: {shares:.2f} shares (~${usd_value:.2f})")
            else:
                lines.append(f"    NO: {shares:.2f} shares")
    
    # Abstract
    abstract_yes = positions['abstract']['yes']
    abstract_no = positions['abstract']['no']
    if abstract_yes > 0 or abstract_no > 0:
        has_positions = True
        lines.append("  Abstract:")
        if abstract_yes > 0:
            shares = abstract_yes / 1e6
            price = checker.get_token_price(MARKET_TOKENS['abstract']['yes'])
            usd_value = shares * price if price > 0 else 0
            if usd_value > 0:
                lines.append(f"    YES: {shares:.2f} shares (~${usd_value:.2f})")
            else:
                lines.append(f"    YES: {shares:.2f} shares")
        if abstract_no > 0:
            shares = abstract_no / 1e6
            price = checker.get_token_price(MARKET_TOKENS['abstract']['no'])
            usd_value = shares * price if price > 0 else 0
            if usd_value > 0:
                lines.append(f"    NO: {shares:.2f} shares (~${usd_value:.2f})")
            else:
                lines.append(f"    NO: {shares:.2f} shares")
    
    # Extended
    extended_yes = positions['extended']['yes']
    extended_no = positions['extended']['no']
    if extended_yes > 0 or extended_no > 0:
        has_positions = True
        lines.append("  Extended:")
        if extended_yes > 0:
            shares = extended_yes / 1e6
            price = checker.get_token_price(MARKET_TOKENS['extended']['yes'])
            usd_value = shares * price if price > 0 else 0
            if usd_value > 0:
                lines.append(f"    YES: {shares:.2f} shares (~${usd_value:.2f})")
            else:
                lines.append(f"    YES: {shares:.2f} shares")
        if extended_no > 0:
            shares = extended_no / 1e6
            price = checker.get_token_price(MARKET_TOKENS['extended']['no'])
            usd_value = shares * price if price > 0 else 0
            if usd_value > 0:
                lines.append(f"    NO: {shares:.2f} shares (~${usd_value:.2f})")
            else:
                lines.append(f"    NO: {shares:.2f} shares")
    
    if not has_positions:
        lines.append("  No positions yet")
    
    return "\n".join(lines)


# Helper function
def check_user_balance(eoa_address: str, safe_address: str = None) -> str:
  
    checker = BalanceChecker()
    balance = checker.get_full_balance(eoa_address, safe_address)
    return format_balance_message(balance)
