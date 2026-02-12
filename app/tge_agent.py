"""
TGE Agent - Autonomous decision-making engine
Integrates: PredictOS + Dome API + x402
"""
import asyncio
from typing import Dict, Optional
from integrations.predictos_client import PredictOSClient
from integrations.dome_client import DomeClientAsync as DomeClient
from integrations.x402_client import X402Client
from tge_alert_config import find_keywords, DEFAULT_TGE_KEYWORDS


class TGEAgent:
    def __init__(self):
        self.predictos = PredictOSClient()
        self.dome = DomeClient()
        self.x402 = X402Client()

    async def analyze_signal(
        self,
        message_content: str,
        project_name: str,
        channel_info: Dict,
        max_trade_amount: float = 10.0,
    ) -> Dict:
        """
        Full agent decision pipeline for hackathon demo.
        """
        # STEP 1: Basic keyword check
        keywords_found = find_keywords(message_content, DEFAULT_TGE_KEYWORDS)
        if not keywords_found:
            return {
                "action": "ignore",
                "confidence": 0.0,
                "reasoning": "No TGE-related keywords detected",
                "keywords_found": [],
            }

        # STEP 2: PredictOS Analysis
        predictos_result = await self.predictos.analyze_tge_signal(
            message_text=message_content, project_name=project_name
        )

        confidence = predictos_result.get("confidence", 0.0)
        intent = predictos_result.get("intent", "unknown")

        if confidence < 0.5:
            return {
                "action": "ignore",
                "confidence": confidence,
                "reasoning": f"Low confidence signal ({confidence:.1%}). Intent: {intent}",
                "predictos_analysis": predictos_result,
                "keywords_found": keywords_found,
            }

        # STEP 3: x402 Tool Discovery
        discovered_tools = await self.x402.discover_tools(
            query=f"polymarket prediction market {project_name} TGE"
        )

        # STEP 4: Dome API Market Intelligence
        market_data = await self.dome.search_markets(project_name)

        if not market_data.get("markets_found"):
            return {
                "action": "monitor",
                "confidence": confidence,
                "reasoning": f"High confidence signal ({confidence:.1%}) but no relevant markets found on Polymarket",
                "predictos_analysis": predictos_result,
                "discovered_tools": discovered_tools,
                "keywords_found": keywords_found,
            }

        best_market = market_data["best_market"]
        opportunity_score = best_market.get("opportunity_score", 0.0)

        # STEP 5: Decision Logic
        should_trade = (
            confidence > 0.7 and opportunity_score > 0.6 and best_market.get("liquidity", 0) > 500
        )

        if should_trade:
            trade_amount = self._calculate_position_size(confidence=confidence, max_amount=max_trade_amount)

            return {
                "action": "trade",
                "confidence": confidence,
                "reasoning": f"All conditions met: confidence {confidence:.1%}, opportunity {opportunity_score:.1%}, liquidity ${best_market.get('liquidity',0):,.0f}",
                "predictos_analysis": predictos_result,
                "market_data": market_data,
                "discovered_tools": discovered_tools,
                "keywords_found": keywords_found,
                "trade_params": {
                    "market_id": best_market.get("market_id"),
                    "question": best_market.get("question"),
                    "side": "YES",
                    "amount_usdc": trade_amount,
                    "expected_price": best_market.get("current_yes_price"),
                    "clob_token_yes": best_market.get("clob_token_yes"),
                },
            }

        # Not trading, provide reasoning
        reasons = []
        if confidence <= 0.7:
            reasons.append(f"Confidence {confidence:.1%} below 70% threshold")
        if opportunity_score <= 0.6:
            reasons.append(f"Opportunity score {opportunity_score:.1%} below 60%")
        if best_market.get("liquidity", 0) <= 500:
            reasons.append(f"Liquidity ${best_market.get('liquidity',0):,.0f} below $500 minimum")

        return {
            "action": "monitor",
            "confidence": confidence,
            "reasoning": "Trade conditions not met: " + "; ".join(reasons),
            "predictos_analysis": predictos_result,
            "market_data": market_data,
            "discovered_tools": discovered_tools,
            "keywords_found": keywords_found,
        }

    def _calculate_position_size(self, confidence: float, max_amount: float) -> float:
        min_pct = 0.2
        scale = min_pct + (1.0 - min_pct) * confidence
        amount = max_amount * scale
        return round(amount, 2)
