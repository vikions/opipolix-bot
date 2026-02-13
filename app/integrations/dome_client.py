"""
Real Dome API Integration using official SDK
Docs: https://api.domeapi.io/
SDK: pip install dome-api-sdk
"""

import os
import time
from typing import Dict, List, Optional
from dome_api_sdk import DomeClient as DomeSDK


class DomeClient:
    """
    Dome API client for Polymarket market intelligence
    
    Uses official dome-api-sdk to:
    - Search markets by keywords
    - Get market details (liquidity, prices, volume)
    - Calculate opportunity scores for agent decisions
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('DOME_API_KEY')
        
        if not self.api_key:
            raise ValueError("DOME_API_KEY not found in environment. Add to .env file.")
        
        # Initialize official Dome SDK
        self.dome = DomeSDK({
            "api_key": self.api_key
        })
        
        print(f"✅ Dome API client initialized")

    @staticmethod
    def _market_to_dict(market) -> dict:
        """Convert a Dome SDK Market object to a plain dict."""
        if isinstance(market, dict):
            return market
        # Try SDK / pydantic serialization methods first
        for method in ('to_dict', 'model_dump', 'dict'):
            fn = getattr(market, method, None)
            if callable(fn):
                try:
                    return fn()
                except Exception:
                    continue
        # Fall back to __dict__
        if hasattr(market, '__dict__'):
            return {k: v for k, v in market.__dict__.items() if not k.startswith('_')}
        print(f"⚠️ Unknown Dome market type: {type(market)}, attrs: {dir(market)}")
        return vars(market)

    @staticmethod
    def _safe_get(obj, key: str, default=None):
        """Get a value from a dict OR an SDK object attribute.
        
        Handles both dict access and pydantic models that may raise
        KeyError from __getattr__ (not just AttributeError).
        """
        if isinstance(obj, dict):
            return obj.get(key, default)
        try:
            return getattr(obj, key)
        except Exception:
            return default

    def _dome_search(self, query: str, limit: int) -> list:
        """Run a single Dome SDK search and return raw market list."""
        response = self.dome.polymarket.markets.get_markets({
            "search": query,
            "status": "open",
            "limit": limit,
        })
        
        # Debug logging to understand SDK response structure
        print(f"🔍 Dome SDK response type: {type(response)}")
        print(f"   Has 'markets': {hasattr(response, 'markets')}")
        
        raw = response.markets if hasattr(response, 'markets') else []
        # Convert SDK objects to dicts
        markets = []
        for m in raw:
            try:
                markets.append(self._market_to_dict(m))
            except Exception as e:
                print(f"⚠️ Could not convert market object: {e}, type={type(m)}")
        return markets

    def search_markets(self, project_name: str, limit: int = 20) -> Dict:
        """
        Search Polymarket markets related to project (synchronous - uses Dome SDK).

        Uses the Dome ``search`` parameter for server-side filtering, then tries
        progressively broader search terms if the first query returns nothing.

        Args:
            project_name: Project name to search for (e.g. "base", "metamask")
            limit: Max markets to return

        Returns:
            {
                "markets_found": [...],
                "best_market": {...} or None,
                "total_count": int,
                "source": "Dome API (real)"
            }
        """

        try:
            # Build search variations: exact term first, then broader phrases
            search_terms = [
                project_name,
                f"{project_name} token",
                f"{project_name} launch",
            ]

            all_markets: list = []
            used_term = project_name

            for term in search_terms:
                print(f"🔍 Dome search: '{term}'")
                results = self._dome_search(term, limit)
                if results:
                    all_markets = results
                    used_term = term
                    break

            if not all_markets:
                print(f"❌ No Dome results for any variation of '{project_name}'")
                return self._empty_response()

            first_title = all_markets[0].get('title', '?') if all_markets else '?'
            print(f"✅ Dome found {len(all_markets)} markets for '{used_term}' "
                  f"(first: {first_title})")

            # Transform to our format and enrich
            enriched_markets = []
            for market in all_markets:
                try:
                    enriched = self._transform_market(market)
                    enriched_markets.append(enriched)
                except Exception as e:
                    print(f"⚠️ Failed to transform market: {e}")

            if not enriched_markets:
                return self._empty_response()

            enriched_markets.sort(key=lambda m: m['opportunity_score'], reverse=True)

            return {
                "markets_found": enriched_markets,
                "best_market": enriched_markets[0],
                "total_count": len(enriched_markets),
                "source": "Dome API (real)"
            }

        except Exception as e:
            print(f"❌ Error calling Dome API: {e}")
            return self._fallback_response(project_name)
    
    def _transform_market(self, market) -> dict:
        """
        Transform Dome API market (dict or SDK object) to our agent format.

        Dome market structure:
        - market_slug: unique identifier
        - title: question text (e.g. "Will Base launch a token by June 30, 2026?")
        - tags: ["Crypto", "Pre-Market", "Token Sales"] etc
        - condition_id: contract identifier
        - start_time, end_time: unix timestamps
        - volume_1_week, volume_1_month, volume_total: trading volume
        - side_a, side_b: {id, label} (Yes/No options)
        """
        g = self._safe_get  # shorthand

        market_id = g(market, 'market_slug', '')
        question = g(market, 'title', '')  # e.g. "Will Base launch a token by June 30, 2026?"
        end_time = g(market, 'end_time', None)
        
        # Determine if market is still open (end_time in future)
        is_open = end_time is not None and end_time > time.time()

        # Volume data
        volume_total = float(g(market, 'volume_total', 0) or 0)
        volume_week = float(g(market, 'volume_1_week', 0) or 0)
        volume_month = float(g(market, 'volume_1_month', 0) or 0)

        volume_24h = volume_week / 7 if volume_week > 0 else volume_month / 30

        # Sides — may be dicts or SDK objects
        side_a_raw = g(market, 'side_a', None)
        side_b_raw = g(market, 'side_b', None)
        side_a = self._market_to_dict(side_a_raw) if side_a_raw and not isinstance(side_a_raw, dict) else (side_a_raw or {})
        side_b = self._market_to_dict(side_b_raw) if side_b_raw and not isinstance(side_b_raw, dict) else (side_b_raw or {})

        # Estimate liquidity from volume (rough proxy)
        estimated_liquidity = volume_total * 0.3

        # Placeholder prices (need orderbook for real prices)
        yes_price = 0.5
        no_price = 0.5

        enriched = {
            "market_id": market_id,
            "question": question,
            "liquidity": estimated_liquidity,
            "current_yes_price": yes_price,
            "current_no_price": no_price,
            "volume_24h": volume_24h,
            "volume_total": volume_total,
            "active": is_open,  # True if end_time > now
            "end_date": end_time,
            "tags": g(market, 'tags', []) or [],  # ["Crypto", "Pre-Market", "Token Sales"]
            "url": f"https://polymarket.com/market/{market_id}",
            "dome_raw": {
                "condition_id": g(market, 'condition_id', None),
                "side_a_label": self._safe_get(side_a, 'label', None),
                "side_b_label": self._safe_get(side_b, 'label', None),
            },
        }

        enriched['opportunity_score'] = self._calculate_opportunity_score(enriched)
        return enriched
    
    def _calculate_opportunity_score(self, market: Dict) -> float:
        """
        Calculate trading opportunity score (0.0 - 1.0)
        
        Factors:
        - Liquidity (40%): Higher is better
        - Price uncertainty (30%): Closer to 50/50 is better opportunity
        - Volume (30%): Higher recent activity is better
        """
        
        # 1. Liquidity score (normalized to $10k)
        liquidity_score = min(market.get('liquidity', 0) / 10000, 1.0)
        
        # 2. Price uncertainty (50/50 = max opportunity)
        yes_price = market.get('current_yes_price', 0.5)
        price_uncertainty = 1.0 - abs(0.5 - yes_price) * 2
        
        # 3. Volume score (normalized to $5k/day)
        volume_24h = market.get('volume_24h', 0)
        volume_score = min(volume_24h / 5000, 1.0)
        
        # Weighted combination
        opportunity = (
            liquidity_score * 0.4 +
            price_uncertainty * 0.3 +
            volume_score * 0.3
        )
        
        return round(opportunity, 3)
    
    def _empty_response(self) -> Dict:
        """Return when no markets found"""
        return {
            "markets_found": [],
            "best_market": None,
            "total_count": 0,
            "source": "Dome API (real)"
        }
    
    def _fallback_response(self, project_name: str) -> Dict:
        """
        Fallback mock data if Dome API fails
        Ensures demo keeps working even if API has issues
        """
        
        print(f"⚠️ Using fallback mock for {project_name} (Dome API unavailable)")
        
        return {
            "markets_found": [{
                "market_id": f"fallback_{project_name.lower()}",
                "question": f"Will {project_name} launch TGE in Q1 2025?",
                "description": f"Fallback market for {project_name}",
                "liquidity": 5000.0,
                "current_yes_price": 0.45,
                "current_no_price": 0.55,
                "volume_24h": 1000.0,
                "volume_total": 8000.0,
                "active": True,
                "tags": ["TGE", "fallback"],
                "opportunity_score": 0.60,
                "url": "https://polymarket.com"
            }],
            "best_market": {
                "market_id": f"fallback_{project_name.lower()}",
                "question": f"Will {project_name} launch TGE in Q1 2025?",
                "liquidity": 5000.0,
                "current_yes_price": 0.45,
                "opportunity_score": 0.60
            },
            "total_count": 1,
            "source": "Dome API (fallback mock)"
        }


# Async wrapper for compatibility with agent code
import asyncio

class DomeClientAsync:
    """Async wrapper for Dome SDK (which is synchronous)"""
    
    def __init__(self, api_key: str = None):
        self.client = DomeClient(api_key)
    
    async def search_markets(self, project_name: str, limit: int = 20) -> Dict:
        """Async version of search_markets"""
        # Run sync Dome SDK call in thread pool
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self.client.search_markets,
            project_name,
            limit,
        )
