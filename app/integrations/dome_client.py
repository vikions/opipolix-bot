"""
Real Dome API Integration using official SDK
Docs: https://api.domeapi.io/
SDK: pip install dome-api-sdk
"""

import os
import time
import requests
from typing import Dict, List, Optional
# Note: dome-api-sdk has a bug with 'status' field, so we use direct HTTP requests
# from dome_api_sdk import DomeClient as DomeSDK


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

        # Use direct HTTP requests to avoid SDK bugs
        self.base_url = "https://api.domeapi.io/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        print(f"✅ Dome API client initialized (direct HTTP mode)")

    @staticmethod
    def _market_to_dict(market) -> dict:
        """Convert market data to dict. Now just returns as-is since we get JSON directly."""
        return market if isinstance(market, dict) else {}

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
        """Run a direct HTTP request to Dome API and return raw market list."""
        try:
            # Use direct HTTP request to avoid SDK bugs with 'status' field
            params = {
                "search": query,
                "status": "open",
                "limit": limit,
            }

            response = requests.get(
                f"{self.base_url}/polymarket/markets",
                headers=self.headers,
                params=params,
                timeout=10
            )

            response.raise_for_status()
            data = response.json()

            # Debug logging
            print(f"🔍 Dome API response status: {response.status_code}")
            print(f"   Response has 'markets': {'markets' in data}")

            markets = data.get('markets', [])
            print(f"   Found {len(markets)} markets")

            return markets
        except requests.exceptions.RequestException as e:
            print(f"❌ Dome API request failed: {e}")
            # Re-raise to be caught by caller's error handling
            raise

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

            print(f"✅ Dome found {len(all_markets)} markets for '{used_term}'")

            # Transform to our format and enrich
            enriched_markets = []
            for market in all_markets:
                try:
                    enriched = self._transform_market(market)
                    # Calculate relevance score for filtering
                    enriched['relevance_score'] = self._calculate_relevance(market, project_name)
                    enriched_markets.append(enriched)
                except Exception as e:
                    print(f"⚠️ Failed to transform market: {e}")

            if not enriched_markets:
                return self._empty_response()

            # Filter for most relevant markets (relevance > 0.3)
            relevant_markets = [m for m in enriched_markets if m.get('relevance_score', 0) > 0.3]

            if not relevant_markets:
                print(f"⚠️ No relevant markets found (all scored < 0.3), using all results")
                relevant_markets = enriched_markets
            else:
                print(f"📊 Filtered to {len(relevant_markets)} relevant markets (out of {len(enriched_markets)})")

            # Sort by opportunity score (liquidity, volume, etc.)
            relevant_markets.sort(key=lambda m: m['opportunity_score'], reverse=True)

            # Log top result for debugging
            if relevant_markets:
                top = relevant_markets[0]
                print(f"🎯 Best market: {top.get('question', '?')[:80]}... "
                      f"(relevance: {top.get('relevance_score', 0):.2f}, "
                      f"opportunity: {top.get('opportunity_score', 0):.2f})")

            enriched_markets = relevant_markets

            return {
                "markets_found": enriched_markets,
                "best_market": enriched_markets[0],
                "total_count": len(enriched_markets),
                "source": "Dome API (real)"
            }

        except Exception as e:
            import traceback
            print(f"❌ Error calling Dome API: {type(e).__name__}: {e}")
            print(f"📋 Full traceback:\n{traceback.format_exc()}")
            # Return empty response instead of fallback to avoid masking real errors
            return self._empty_response()
    
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
    
    def _calculate_relevance(self, market: dict, project_name: str) -> float:
        """
        Calculate how relevant this market is to the project search (0.0 - 1.0)

        Checks:
        - Exact project name match in title/tags (high score)
        - TGE/token/launch keywords in title (medium score)
        - Project name in description (low score)
        """
        score = 0.0
        project_lower = project_name.lower()

        # Get market text fields
        title = self._safe_get(market, 'title', '').lower()
        tags = [str(t).lower() for t in (self._safe_get(market, 'tags', None) or [])]
        description = self._safe_get(market, 'description', '') or ''
        description_lower = description.lower()

        # 1. Exact project name in title (0.6 points)
        if project_lower in title:
            score += 0.6

        # 2. Project name in tags (0.3 points)
        for tag in tags:
            if project_lower in tag:
                score += 0.3
                break

        # 3. TGE/token/launch keywords in title (0.2 points)
        tge_keywords = ['tge', 'token', 'launch', 'airdrop', 'pre-market', 'token sales']
        for keyword in tge_keywords:
            if keyword in title:
                score += 0.2
                break

        # 4. Project name in description (0.1 points)
        if project_lower in description_lower:
            score += 0.1

        return min(score, 1.0)  # Cap at 1.0

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
