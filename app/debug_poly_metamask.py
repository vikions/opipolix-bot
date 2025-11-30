# app/debug_poly_metamask.py
from polymarket_client import fetch_raw_polymarket_markets

markets = fetch_raw_polymarket_markets(20)
for m in markets:
    if "MetaMask" in m.get("question", "") or "Meta" in m.get("question", ""):
        print(m.get("id"), m.get("question"))
