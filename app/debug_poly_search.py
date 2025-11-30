import requests

BASE_URL = "https://gamma-api.polymarket.com"

def search_polymarket_markets(query: str):
    resp = requests.get(f"{BASE_URL}/search", params={"query": query}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data

def main():
    query = "MetaMask"
    print(f"🔍 Searching Polymarket for '{query}'...\n")
    results = search_polymarket_markets(query)

    if not results:
        print("❌ Ничего не найдено")
        return

    for r in results:
        print(
            "\n📌 Market Found:",
            "\nID:", r.get("id"),
            "\nQuestion:", r.get("question") or r.get("title") or "N/A",
            "\nSlug:", r.get("slug"),
            "\n---"
        )

if __name__ == "__main__":
    main()
