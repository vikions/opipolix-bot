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

# Known Polymarket CLOB token IDs from our trading system.
# Used as fallback when Dome API doesn't return clob_token_yes.
KNOWN_MARKET_TOKENS = {
    "metamask": {
        "clob_token_yes": "110325437323003864440364193681628128179433892752231328064623776035311134623682",
        "market_id": "657287",
        "keywords": ["metamask"],
    },
    "base": {
        "clob_token_yes": "73916079699906389194973750600611907885736641148308464550611829122042479621960",
        "market_id": "821172",
        "keywords": ["base"],
    },
    "abstract": {
        "clob_token_yes": "105292534464588119413823901919588224897612305776681795693919323419047416388812",
        "market_id": "718188",
        "keywords": ["abstract"],
    },
    "extended": {
        "clob_token_yes": "80202018619101908013933944100239367385491528832020028327612486898619283802751",
        "market_id": "690612",
        "keywords": ["extended"],
    },
    "megaeth": {
        "clob_token_yes": "96797656031191119176188453471637044475353637081608890153571023284371119486681",
        "market_id": "556108",
        "keywords": ["megaeth", "mega"],
    },
    "opinion": {
        "clob_token_yes": "93726420352633513329470759167746705807552087459747684830196318055992489326724",
        "market_id": "1280497",
        "keywords": ["opinion"],
    },
    "opensea": {
        "clob_token_yes": "27454650606007592941369542547867915436927994811369993520265431958254270690528",
        "market_id": "1271610",
        "keywords": ["opensea", "sea"],
    },
}


class TGEAgent:
    def __init__(self):
        self.predictos = PredictOSClient()
        self.dome = DomeClient()
        self.x402 = X402Client()

    def _resolve_known_token(self, project_name: str) -> Optional[Dict]:
        """Match project_name against KNOWN_MARKET_TOKENS by keyword substring."""
        name_lower = project_name.lower()
        for token_info in KNOWN_MARKET_TOKENS.values():
            for kw in token_info["keywords"]:
                if kw in name_lower:
                    return token_info
        return None

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
        # Normalize project name for consistent matching
        project_name = project_name.strip().lower()

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

        # Resolve known token early for fallback
        known = self._resolve_known_token(project_name)

        # STEP 4: Dome API Market Intelligence
        market_data = await self.dome.search_markets(project_name)

        if not market_data.get("markets_found"):
            # Fallback: if we have a known token, still allow trading
            if known and confidence > 0.7:
                trade_amount = self._calculate_position_size(confidence=confidence, max_amount=max_trade_amount)
                return {
                    "action": "trade",
                    "confidence": confidence,
                    "reasoning": f"High confidence signal ({confidence:.1%}), no Dome results but matched known market",
                    "predictos_analysis": predictos_result,
                    "discovered_tools": discovered_tools,
                    "keywords_found": keywords_found,
                    "trade_params": {
                        "market_id": known["market_id"],
                        "question": f"{project_name} TGE",
                        "side": "YES",
                        "amount_usdc": trade_amount,
                        "expected_price": None,
                        "clob_token_yes": known["clob_token_yes"],
                    },
                }

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

            # Use Dome's clob_token_yes if available, otherwise fall back to known tokens
            clob_token = best_market.get("clob_token_yes")
            market_id = best_market.get("market_id")
            if not clob_token and known:
                clob_token = known["clob_token_yes"]
                market_id = market_id or known["market_id"]

            return {
                "action": "trade",
                "confidence": confidence,
                "reasoning": f"All conditions met: confidence {confidence:.1%}, opportunity {opportunity_score:.1%}, liquidity ${best_market.get('liquidity',0):,.0f}",
                "predictos_analysis": predictos_result,
                "market_data": market_data,
                "discovered_tools": discovered_tools,
                "keywords_found": keywords_found,
                "trade_params": {
                    "market_id": market_id,
                    "question": best_market.get("question"),
                    "side": "YES",
                    "amount_usdc": trade_amount,
                    "expected_price": best_market.get("current_yes_price"),
                    "clob_token_yes": clob_token,
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
