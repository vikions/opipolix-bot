from opinion_client import client

def main():
    market_id = 793  # тот самый из ссылки
    res = client.get_market(market_id)
    print("errno =", res.errno)
    print("errmsg =", res.errmsg)
    if res.errno == 0:
        m = res.result.data
        print("market_id:", m.market_id)
        print("title:", m.market_title)
        print("status:", m.status)

if __name__ == "__main__":
    main()
