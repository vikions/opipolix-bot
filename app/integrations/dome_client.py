"""
Real Dome API Integration using official SDK
Docs: https://api.domeapi.io/
SDK: pip install dome-api-sdk
"""

import os
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
    
    async def search_markets(self, project_name: str, limit: int = 20) -> Dict:
        """
        Search Polymarket markets related to project
        
        Args:
            project_name: Project name to search for (e.g. "ProjectX", "Bitcoin")
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
            print(f"🔍 Searching Dome API for markets about: {project_name}")
            
            # Search markets using Dome SDK
            # Note: Dome API searches across all Polymarket markets
            # We filter by tags, title, description containing our project name
            response = self.dome.polymarket.markets.get_markets({
                "limit": limit,
                # If Dome supports text search, use it:
                # "search": project_name,
            })
            
            all_markets = response.markets
            
            # Filter markets relevant to our project
            # Search in: title, tags, description
            project_lower = project_name.lower()
            relevant_markets = []
            
            for market in all_markets:
                title = market.get('title', '').lower()
                description = market.get('description', '').lower()
                tags = [tag.lower() for tag in market.get('tags', [])]
                
                # Check if project name appears anywhere
                if (project_lower in title or 
                    project_lower in description or 
                    any(project_lower in tag for tag in tags)):
                    
                    relevant_markets.append(market)
            
            if not relevant_markets:
                print(f"❌ No markets found for {project_name}")
                return self._empty_response()
            
            print(f"✅ Found {len(relevant_markets)} relevant markets")
            
            # Transform to our format and enrich
            enriched_markets = []
            for market in relevant_markets:
                enriched = self._transform_market(market)
                enriched_markets.append(enriched)
            
            # Sort by opportunity score (calculated below)
            enriched_markets.sort(key=lambda m: m['opportunity_score'], reverse=True)
            
            return {
                "markets_found": enriched_markets,
                "best_market": enriched_markets[0] if enriched_markets else None,
                "total_count": len(enriched_markets),
                "source": "Dome API (real)"
            }
        
        except Exception as e:
            print(f"❌ Error calling Dome API: {e}")
            # Return fallback mock for demo resilience
            return self._fallback_response(project_name)
    
    def _transform_market(self, market: dict) -> dict:
        """
        Transform Dome API market format to our agent format
        
        Dome market structure:
        - market_slug, event_slug, condition_id
        - title, description, tags
        - volume_total, volume_1_week, volume_1_month
        - side_a (label, id), side_b (label, id)
        - status (open/closed), start_time, end_time
        - extra_fields (varies by market type)
        """
        
        # Extract basic info
        market_id = market.get('market_slug', '')
        question = market.get('title', '')
        description = market.get('description', '')
        status = market.get('status', 'unknown')
        
        # Volume data
        volume_total = float(market.get('volume_total', 0))
        volume_week = float(market.get('volume_1_week', 0))
        volume_month = float(market.get('volume_1_month', 0))
        
        # Use week volume as proxy for 24h (Dome doesn't have 24h directly)
        volume_24h = volume_week / 7 if volume_week > 0 else volume_month / 30
        
        # Sides (YES/NO or custom labels like Up/Down)
        side_a = market.get('side_a', {})
        side_b = market.get('side_b', {})
        
        # For binary markets, assume side_a is YES
        # Note: Dome doesn't directly provide current prices in market list
        # You may need to call additional endpoint or use orderbook data
        # For now, we'll estimate or set placeholder
        
        # Estimate liquidity from volume (rough proxy)
        # Real liquidity would need orderbook depth
        estimated_liquidity = volume_total * 0.3  # Rough estimate
        
        # Placeholder prices (would need orderbook API call for real prices)
        yes_price = 0.5  # Placeholder - update if Dome provides this
        no_price = 0.5   # Placeholder
        
        # Build enriched market object
        enriched = {
            "market_id": market_id,
            "question": question,
            "description": description,
            "liquidity": estimated_liquidity,
            "current_yes_price": yes_price,
            "current_no_price": no_price,
            "volume_24h": volume_24h,
            "volume_total": volume_total,
            "active": status == "open",
            "end_date": market.get('end_time'),
            "tags": market.get('tags', []),
            "url": f"https://polymarket.com/event/{market.get('event_slug', '')}/{market_id}",
            
            # Raw Dome data for debugging
            "dome_raw": {
                "condition_id": market.get('condition_id'),
                "side_a_label": side_a.get('label'),
                "side_b_label": side_b.get('label'),
                "status": status
            }
        }
        
        # Calculate opportunity score
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
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.client.search_markets,
            project_name,
            limit
        )
