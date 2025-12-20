
import os
import time
import json
from typing import Dict, Optional
from dotenv import load_dotenv


from py_builder_signing_sdk.config import BuilderConfig, BuilderApiKeyCreds
from py_builder_signing_sdk.sdk_types import RemoteBuilderConfig, BuilderHeaderPayload

load_dotenv()


RELAYER_URL = os.environ.get("RELAYER_URL", "https://relayer-v2.polymarket.com")
BUILDER_SIGNING_URL = os.environ.get("BUILDER_SIGNING_URL")
CHAIN_ID = 137  # Polygon Mainnet


BUILDER_API_KEY = os.environ.get("BUILDER_API_KEY")
BUILDER_SECRET = os.environ.get("BUILDER_SECRET")
BUILDER_PASS_PHRASE = os.environ.get("BUILDER_PASS_PHRASE")

# Contract addresses (Polygon Mainnet)
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
CTF_ADDRESS = "0x4d97dcd97ec945f40cf65f87097ace5ea0476045"
CTF_EXCHANGE = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"

# Import RelayClient
from py_builder_relayer_client.client import RelayClient


class UserRelayerClient:
    
    
    def __init__(self, user_private_key: str, telegram_id: Optional[int] = None):
        
        self.telegram_id = telegram_id
        self.private_key = user_private_key
        
        
        if BUILDER_API_KEY and BUILDER_SECRET and BUILDER_PASS_PHRASE:
            print("🔑 Using LOCAL builder credentials (temporary)")
            builder_config = BuilderConfig(
                local_builder_creds=BuilderApiKeyCreds(
                    key=BUILDER_API_KEY,
                    secret=BUILDER_SECRET,
                    passphrase=BUILDER_PASS_PHRASE
                )
            )
        elif BUILDER_SIGNING_URL:
            print("🔐 Using REMOTE builder signing")
            remote_config = RemoteBuilderConfig(url=BUILDER_SIGNING_URL)
            builder_config = BuilderConfig(remote_builder_config=remote_config)
        else:
            raise ValueError(
                "Builder credentials not configured!\n"
                "Set either BUILDER_API_KEY+SECRET+PASSPHRASE or BUILDER_SIGNING_URL"
            )
        
        
        self.client = RelayClient(
            RELAYER_URL,
            CHAIN_ID,
            self.private_key,
            builder_config
        )
    
    def deploy_safe(self) -> Dict:
        """
        Deploy Safe wallet (GASLESS!)
        
        Returns:
            dict: {
                'safe_address': str or None,
                'tx_hash': str or None,
                'status': 'success' | 'failed' | 'error',
                'error': str (if error)
            }
        """
        try:
            print(f"🚀 Deploying Safe for user {self.telegram_id}...")
            
            
            try:
                expected_safe = self.client.get_expected_safe()
                is_deployed = self.client.get_deployed(expected_safe)
                
                if is_deployed:
                    print(f"✅ Safe already deployed: {expected_safe}")
                    return {
                        'safe_address': expected_safe,
                        'tx_hash': None,  
                        'status': 'success'
                    }
            except Exception as e:
                print(f"Could not check deployment status: {e}")
            
            
            response = self.client.deploy()
            result = response.wait()
            
            if result:
                
                safe_address = result.get('proxyAddress') or result.get('proxy_address')
                tx_hash = result.get('transactionHash') or result.get('transaction_hash')
                
                print(f"✅ Safe deployed: {safe_address}")
                return {
                    'safe_address': safe_address,
                    'tx_hash': tx_hash,
                    'status': 'success'
                }
            else:
                print(f"❌ Safe deployment failed")
                return {
                    'safe_address': None,
                    'tx_hash': None,
                    'status': 'failed'
                }
        except Exception as e:
            error_msg = str(e)
            
            
            if "already deployed" in error_msg.lower():
                
                import re
                match = re.search(r'0x[a-fA-F0-9]{40}', error_msg)
                if match:
                    safe_address = match.group(0)
                    print(f"✅ Safe already deployed: {safe_address}")
                    return {
                        'safe_address': safe_address,
                        'tx_hash': None,
                        'status': 'success'
                    }
            
            print(f"❌ Error deploying Safe: {e}")
            return {
                'safe_address': None,
                'tx_hash': None,
                'status': 'error',
                'error': error_msg
            }
    
    def approve_usdc(self) -> Dict:
        
        try:
            print(f"💰 Approving USDC for user {self.telegram_id}...")
            
            from eth_utils import keccak, to_checksum_address
            from eth_abi import encode
            from py_builder_relayer_client.models import OperationType, SafeTransaction
            
            
            def _function_selector(signature: str) -> bytes:
                return keccak(text=signature)[:4]
            
            selector = _function_selector("approve(address,uint256)")
            encoded_args = encode(
                ["address", "uint256"],
                [to_checksum_address(CTF_EXCHANGE), 2**256 - 1]
            )
            approve_data = "0x" + (selector + encoded_args).hex()
            
            
            safe_tx = SafeTransaction(
                to=to_checksum_address(USDC_ADDRESS),
                operation=OperationType.Call,
                data=approve_data,
                value="0"
            )
            
            response = self.client.execute(
                [safe_tx],
                metadata=f"USDC approve for TG user {self.telegram_id}"
            )
            
            result = response.wait()
            
            if result:
                tx_hash = result.get('transactionHash') or result.get('transaction_hash')
                print(f"✅ USDC approved: {tx_hash}")
                return {
                    'tx_hash': tx_hash,
                    'status': 'success'
                }
            else:
                return {'status': 'failed'}
                
        except Exception as e:
            print(f"❌ Error approving USDC: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def approve_ctf(self) -> Dict:
        
        try:
            print(f"🎯 Approving CTF for user {self.telegram_id}...")
            
            from eth_utils import keccak, to_checksum_address
            from eth_abi import encode
            from py_builder_relayer_client.models import OperationType, SafeTransaction
            
            
            def _function_selector(signature: str) -> bytes:
                return keccak(text=signature)[:4]
            
            selector = _function_selector("setApprovalForAll(address,bool)")
            encoded_args = encode(
                ["address", "bool"],
                [to_checksum_address(CTF_EXCHANGE), True]
            )
            approve_data = "0x" + (selector + encoded_args).hex()
            
            
            safe_tx = SafeTransaction(
                to=to_checksum_address(CTF_ADDRESS),
                operation=OperationType.Call,
                data=approve_data,
                value="0"
            )
            
            response = self.client.execute(
                [safe_tx],
                metadata=f"CTF approve for TG user {self.telegram_id}"
            )
            
            result = response.wait()
            
            if result:
                tx_hash = result.get('transactionHash') or result.get('transaction_hash')
                print(f"✅ CTF approved: {tx_hash}")
                return {
                    'tx_hash': tx_hash,
                    'status': 'success'
                }
            else:
                return {'status': 'failed'}
                
        except Exception as e:
            print(f"❌ Error approving CTF: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def setup_trading(self) -> Dict:
       
        print(f"\n🔧 Setting up trading for user {self.telegram_id}...")
        
        
        safe_result = self.deploy_safe()
        if safe_result['status'] != 'success':
            return {
                'status': 'failed',
                'step': 'deploy_safe',
                'error': safe_result.get('error', 'Failed to deploy Safe')
            }
        
        safe_address = safe_result['safe_address']
        
        
        usdc_result = self.approve_usdc()
        if usdc_result['status'] != 'success':
            return {
                'safe_address': safe_address,
                'safe_tx_hash': safe_result['tx_hash'],
                'status': 'failed',
                'step': 'approve_usdc',
                'error': usdc_result.get('error', 'Failed to approve USDC')
            }
        
        
        ctf_result = self.approve_ctf()
        if ctf_result['status'] != 'success':
            return {
                'safe_address': safe_address,
                'safe_tx_hash': safe_result['tx_hash'],
                'usdc_tx_hash': usdc_result['tx_hash'],
                'status': 'failed',
                'step': 'approve_ctf',
                'error': ctf_result.get('error', 'Failed to approve CTF')
            }
        
        print(f"✅ Trading setup complete for user {self.telegram_id}!")
        
        return {
            'safe_address': safe_address,
            'safe_tx_hash': safe_result['tx_hash'],
            'usdc_tx_hash': usdc_result['tx_hash'],
            'ctf_tx_hash': ctf_result['tx_hash'],
            'status': 'success'
        }



def setup_user_for_trading(user_private_key: str, telegram_id: int) -> Dict:
   
    relayer = UserRelayerClient(user_private_key, telegram_id)
    return relayer.setup_trading()