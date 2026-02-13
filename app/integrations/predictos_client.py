"""
Mock PredictOS client for hackathon demo.
Returns a simple confidence score and intent based on keywords.
"""
import asyncio
from typing import Dict


class PredictOSClient:
    def __init__(self):
        pass

    async def analyze_tge_signal(self, message_text: str, project_name: str = None) -> Dict:
        """Mock analysis: score by counting keywords and length"""
        # Very small async sleep to simulate network call
        await asyncio.sleep(0.1)

        text = (message_text or "").lower()
        keywords = ["tge", "token", "airdrop", "launch", "claim", "listing", "announcement", "announce"]
        hits = sum(1 for k in keywords if k in text)

        # Improved confidence calculation:
        # - 1 keyword: 0.5 (50%) - enough to trigger
        # - 2 keywords: 0.7 (70%) - good signal
        # - 3+ keywords: 0.9 (90%) - strong signal
        confidence = min(0.95, 0.3 + 0.2 * hits)

        intent = "announce" if hits >= 1 else "unknown"

        # Mock extracted data
        extracted = {
            "date_mentioned": any(word.isdigit() for word in text.split()),
            "urgency_score": min(1.0, 0.1 * hits),
        }

        return {
            "confidence": confidence,
            "intent": intent,
            "extracted_data": extracted,
            "raw_text": message_text,
        }
