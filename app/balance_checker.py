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
    },
    "megaeth": {
        "yes": "96797656031191119176188453471637044475353637081608890153571023284371119486681",
        "no": "102844052859529992637803443259193395522411387362312885030298797134413940349829"
    },
    "opinion": {
        "yes": "93726420352633513329470759167746705807552087459747684830196318055992489326724",
        "no": "77149450096247036266517002616170405423637634097737272142741091924214387425694"
    },
    "opensea": {
        "yes": "27454650606007592941369542547867915436927994811369993520265431958254270690528",
        "no": "86113972936256916379383585127599563414935698637842191661881945451738552931124"
    },
    "opinion_fdv": {
        "yes": "50352926775492572007129313229442771572343916931005903007424590093174311630298",
        "no": "24347171758774499938462633574721292772800062019156311729242237473590058137270"
    },
    "opensea_fdv": {
        "yes": "55736535775539231856682158017890031261644294952589300517957218393676136917293",
        "no": "71718402031669298364238907670733752499185585238670546354636156779359681992646"
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
            'extended': {'yes': 0.0, 'no': 0.0},
            'megaeth': {'yes': 0.0, 'no': 0.0},
            'opinion': {'yes': 0.0, 'no': 0.0},
            'opensea': {'yes': 0.0, 'no': 0.0},
            'opinion_fdv': {'yes': 0.0, 'no': 0.0},
            'opensea_fdv': {'yes': 0.0, 'no': 0.0}
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

            # MegaETH positions
            if MARKET_TOKENS['megaeth']['yes'] != 'TBD':
                positions['megaeth']['yes'] = self.get_position_balance(
                    safe_address,
                    MARKET_TOKENS['megaeth']['yes']
                )
                positions['megaeth']['no'] = self.get_position_balance(
                    safe_address,
                    MARKET_TOKENS['megaeth']['no']
                )

            # Opinion token positions
            if MARKET_TOKENS['opinion']['yes'] != 'TBD':
                positions['opinion']['yes'] = self.get_position_balance(
                    safe_address,
                    MARKET_TOKENS['opinion']['yes']
                )
                positions['opinion']['no'] = self.get_position_balance(
                    safe_address,
                    MARKET_TOKENS['opinion']['no']
                )

            # OpenSea token positions
            if MARKET_TOKENS['opensea']['yes'] != 'TBD':
                positions['opensea']['yes'] = self.get_position_balance(
                    safe_address,
                    MARKET_TOKENS['opensea']['yes']
                )
                positions['opensea']['no'] = self.get_position_balance(
                    safe_address,
                    MARKET_TOKENS['opensea']['no']
                )

            # Opinion FDV positions
            if MARKET_TOKENS['opinion_fdv']['yes'] != 'TBD':
                positions['opinion_fdv']['yes'] = self.get_position_balance(
                    safe_address,
                    MARKET_TOKENS['opinion_fdv']['yes']
                )
                positions['opinion_fdv']['no'] = self.get_position_balance(
                    safe_address,
                    MARKET_TOKENS['opinion_fdv']['no']
                )

            # Opensea FDV positions
            if MARKET_TOKENS['opensea_fdv']['yes'] != 'TBD':
                positions['opensea_fdv']['yes'] = self.get_position_balance(
                    safe_address,
                    MARKET_TOKENS['opensea_fdv']['yes']
                )
                positions['opensea_fdv']['no'] = self.get_position_balance(
                    safe_address,
                    MARKET_TOKENS['opensea_fdv']['no']
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

    # MegaETH
    megaeth_yes = positions['megaeth']['yes']
    megaeth_no = positions['megaeth']['no']
    if megaeth_yes > 0 or megaeth_no > 0:
        has_positions = True
        lines.append("  MegaETH:")
        if megaeth_yes > 0:
            shares = megaeth_yes / 1e6
            price = checker.get_token_price(MARKET_TOKENS['megaeth']['yes'])
            usd_value = shares * price if price > 0 else 0
            if usd_value > 0:
                lines.append(f"    YES: {shares:.2f} shares (~${usd_value:.2f})")
            else:
                lines.append(f"    YES: {shares:.2f} shares")
        if megaeth_no > 0:
            shares = megaeth_no / 1e6
            price = checker.get_token_price(MARKET_TOKENS['megaeth']['no'])
            usd_value = shares * price if price > 0 else 0
            if usd_value > 0:
                lines.append(f"    NO: {shares:.2f} shares (~${usd_value:.2f})")
            else:
                lines.append(f"    NO: {shares:.2f} shares")

    # Opinion Token
    opinion_yes = positions['opinion']['yes']
    opinion_no = positions['opinion']['no']
    if opinion_yes > 0 or opinion_no > 0:
        has_positions = True
        lines.append("  Opinion Token:")
        if opinion_yes > 0:
            shares = opinion_yes / 1e6
            price = checker.get_token_price(MARKET_TOKENS['opinion']['yes'])
            usd_value = shares * price if price > 0 else 0
            if usd_value > 0:
                lines.append(f"    YES: {shares:.2f} shares (~${usd_value:.2f})")
            else:
                lines.append(f"    YES: {shares:.2f} shares")
        if opinion_no > 0:
            shares = opinion_no / 1e6
            price = checker.get_token_price(MARKET_TOKENS['opinion']['no'])
            usd_value = shares * price if price > 0 else 0
            if usd_value > 0:
                lines.append(f"    NO: {shares:.2f} shares (~${usd_value:.2f})")
            else:
                lines.append(f"    NO: {shares:.2f} shares")

    # OpenSea Token
    opensea_yes = positions['opensea']['yes']
    opensea_no = positions['opensea']['no']
    if opensea_yes > 0 or opensea_no > 0:
        has_positions = True
        lines.append("  OpenSea Token:")
        if opensea_yes > 0:
            shares = opensea_yes / 1e6
            price = checker.get_token_price(MARKET_TOKENS['opensea']['yes'])
            usd_value = shares * price if price > 0 else 0
            if usd_value > 0:
                lines.append(f"    YES: {shares:.2f} shares (~${usd_value:.2f})")
            else:
                lines.append(f"    YES: {shares:.2f} shares")
        if opensea_no > 0:
            shares = opensea_no / 1e6
            price = checker.get_token_price(MARKET_TOKENS['opensea']['no'])
            usd_value = shares * price if price > 0 else 0
            if usd_value > 0:
                lines.append(f"    NO: {shares:.2f} shares (~${usd_value:.2f})")
            else:
                lines.append(f"    NO: {shares:.2f} shares")

    # Opinion FDV
    fdv_yes = positions['opinion_fdv']['yes']
    fdv_no = positions['opinion_fdv']['no']
    if fdv_yes > 0 or fdv_no > 0:
        has_positions = True
        lines.append("  Opinion FDV:")
        if fdv_yes > 0:
            shares = fdv_yes / 1e6
            price = checker.get_token_price(MARKET_TOKENS['opinion_fdv']['yes'])
            usd_value = shares * price if price > 0 else 0
            if usd_value > 0:
                lines.append(f"    YES: {shares:.2f} shares (~${usd_value:.2f})")
            else:
                lines.append(f"    YES: {shares:.2f} shares")
        if fdv_no > 0:
            shares = fdv_no / 1e6
            price = checker.get_token_price(MARKET_TOKENS['opinion_fdv']['no'])
            usd_value = shares * price if price > 0 else 0
            if usd_value > 0:
                lines.append(f"    NO: {shares:.2f} shares (~${usd_value:.2f})")
            else:
                lines.append(f"    NO: {shares:.2f} shares")

    # Opensea FDV
    opensea_yes = positions['opensea_fdv']['yes']
    opensea_no = positions['opensea_fdv']['no']
    if opensea_yes > 0 or opensea_no > 0:
        has_positions = True
        lines.append("  Opensea FDV:")
        if opensea_yes > 0:
            shares = opensea_yes / 1e6
            price = checker.get_token_price(MARKET_TOKENS['opensea_fdv']['yes'])
            usd_value = shares * price if price > 0 else 0
            if usd_value > 0:
                lines.append(f"    YES: {shares:.2f} shares (~${usd_value:.2f})")
            else:
                lines.append(f"    YES: {shares:.2f} shares")
        if opensea_no > 0:
            shares = opensea_no / 1e6
            price = checker.get_token_price(MARKET_TOKENS['opensea_fdv']['no'])
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
