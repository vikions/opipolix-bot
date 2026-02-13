"""
Mock x402 client for tool discovery demonstration.
"""
import asyncio
from typing import List, Dict


class X402Client:
    def __init__(self):
        pass

    async def discover_tools(self, query: str) -> List[Dict]:
        # Simulate async discovery
        await asyncio.sleep(0.05)
        return [
            {"name": "Polymarket Explorer", "url": "https://polymarket.com"},
            {"name": "Liquidity Monitor", "url": "https://example.com/liquidity"},
        ]
