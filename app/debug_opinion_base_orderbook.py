from opinion_client import client

MARKET_ID = 1270  # Base

def main():
    # 1) Детали рынка
    detail = client.get_market(MARKET_ID)
    print("get_market errno:", detail.errno, "errmsg:", getattr(detail, "errmsg", ""))
    if detail.errno != 0:
        return

    m = detail.result.data
    print("title:", getattr(m, "market_title", None))
    yes_token_id = getattr(m, "yes_token_id", None)
    no_token_id = getattr(m, "no_token_id", None)
    print("yes_token_id:", yes_token_id)
    print("no_token_id :", no_token_id)
    print()

    # 2) Ордербук по YES и NO
    for label, token_id in [("YES", yes_token_id), ("NO", no_token_id)]:
        print(f"===== {label} orderbook for token {token_id} =====")
        if not token_id:
            print("  token_id is None")
            continue

        ob_resp = client.get_orderbook(token_id)
        print("  get_orderbook errno:", ob_resp.errno, "errmsg:", getattr(ob_resp, "errmsg", ""))
        if ob_resp.errno != 0:
            continue

        # наш универсальный поиск «ядра» книги
        ob = ob_resp.result
        if hasattr(ob_resp, "data") and getattr(ob_resp, "data") is not None:
            ob = ob_resp.data

        book = ob
        asks = getattr(book, "asks", [])
        bids = getattr(book, "bids", [])

        print("  asks count:", len(asks))
        for lvl in asks[:5]:
            price = getattr(lvl, "price", None)
            if price is None and isinstance(lvl, dict):
                price = lvl.get("price")
            if price is None and isinstance(lvl, (list, tuple)) and len(lvl) > 0:
                price = lvl[0]
            print("   ask:", price, "raw:", lvl)

        print("  bids count:", len(bids))
        for lvl in bids[:5]:
            price = getattr(lvl, "price", None)
            if price is None and isinstance(lvl, dict):
                price = lvl.get("price")
            if price is None and isinstance(lvl, (list, tuple)) and len(lvl) > 0:
                price = lvl[0]
            print("   bid:", price, "raw:", lvl)

        print()

if __name__ == "__main__":
    main()
