import requests
import json

BASE_URL = "https://gamma-api.polymarket.com"

def main():
    slug = "will-base-launch-a-token-in-2025-341"
    url = f"{BASE_URL}/events/slug/{slug}"
    print(f"🔍 Fetching Polymarket event by slug:\n{url}\n")

    resp = requests.get(url, timeout=10)
    print("Status code:", resp.status_code)

    if resp.status_code != 200:
        print("Body:", resp.text[:1000])
        return

    data = resp.json()
    print("\nRaw JSON (truncated):")
    print(json.dumps(data, indent=2)[:2000])

    markets = data.get("markets") or data.get("eventMarkets") or []
    print(f"\nFound {len(markets)} markets inside this event.\n")

    for m in markets:
        mid = m.get("id") or m.get("_id")
        q = m.get("question") or m.get("title") or m.get("name")
        print("Market ID:", mid)
        print("Question:", q)
        print("---")

if __name__ == "__main__":
    main()
