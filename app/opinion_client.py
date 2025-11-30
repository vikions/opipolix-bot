import os
from typing import Optional

from dotenv import load_dotenv
from opinion_clob_sdk import Client
from opinion_clob_sdk.model import TopicStatusFilter

# Загружаем переменные из .env (который лежит в корне проекта)
load_dotenv()

API_KEY = os.getenv("API_KEY")
HOST = os.getenv("HOST", "https://proxy.opinion.trade:8443")
CHAIN_ID = int(os.getenv("CHAIN_ID", "56"))
RPC_URL = os.getenv("RPC_URL", "")  # можно пустой, если только читаем
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
MULTI_SIG_ADDRESS = os.getenv("MULTI_SIG_ADDRESS")

if not API_KEY:
    raise RuntimeError("API_KEY is not set in .env")

if not PRIVATE_KEY:
    raise RuntimeError("PRIVATE_KEY is not set in .env")

if not MULTI_SIG_ADDRESS:
    raise RuntimeError("MULTI_SIG_ADDRESS is not set in .env")

client = Client(
    host=HOST,
    apikey=API_KEY,
    chain_id=CHAIN_ID,
    rpc_url=RPC_URL,
    private_key=PRIVATE_KEY,
    multi_sig_addr=MULTI_SIG_ADDRESS,
    # можно потом поиграться с кэшем:
    # market_cache_ttl=300,
    # quote_tokens_cache_ttl=3600,
)


def fetch_active_markets(limit: int = 5):
    """Вернуть список активных рынков (первые N штук)."""
    response = client.get_markets(
        status=TopicStatusFilter.ACTIVATED,
        limit=limit,
    )

    if response.errno == 0:
        return response.result.list
    else:
        raise Exception(f"Error {response.errno}: {response.errmsg}")


def get_simple_markets(limit: int = 5):
    """Возвращает список словарей вида: [{'id':..., 'title':...}, ...]"""
    markets = fetch_active_markets(limit)
    simplified = [
        {
            "id": m.market_id,
            "title": m.market_title,
        }
        for m in markets
    ]
    return simplified

def _extract_best_ask_price(book) -> Optional[float]:
    """
    Достаём ЛУЧШУЮ (минимальную) цену продажи (ask) из ордербука Opinion.
    book — это объект, у которого должны быть asks / bids.
    """
    try:
        if not book:
            return None

        asks = getattr(book, "asks", None)
        if not asks:
            return None

        best: Optional[float] = None

        for level in asks:
            # Пытаемся вытащить price из разных возможных форматов
            price = getattr(level, "price", None)

            if price is None and isinstance(level, dict):
                price = level.get("price")

            if price is None and isinstance(level, (list, tuple)) and len(level) > 0:
                price = level[0]

            if price is None:
                continue

            try:
                val = float(price)
            except Exception:
                continue

            if best is None or val < best:
                best = val

        return best

    except Exception:
        return None


def _get_orderbook_core(token_id) -> Optional[object]:
    """
    Пытаемся аккуратно вытащить «ядро» ордербука (объект с bids/asks)
    из ответа client.get_orderbook(...), не падая на .data / .result.
    """
    resp = client.get_orderbook(token_id)

    if getattr(resp, "errno", None) != 0:
        return None

    # Кандидаты, где может лежать книга
    # 1) resp.result.data
    # 2) resp.result
    # 3) resp.data
    # 4) сам resp
    candidates = []

    result_attr = getattr(resp, "result", None)
    if result_attr is not None:
        candidates.append(result_attr)
        inner_data = getattr(result_attr, "data", None)
        if inner_data is not None:
            candidates.append(inner_data)

    data_attr = getattr(resp, "data", None)
    if data_attr is not None:
        candidates.append(data_attr)

    candidates.append(resp)

    for cand in candidates:
        if cand is None:
            continue
        # Если у объекта есть bids/asks — это то, что нам нужно
        if hasattr(cand, "asks") or hasattr(cand, "bids"):
            return cand

    return None


def get_opinion_binary_prices(market_id: int) -> dict:
    """
    Возвращает {'yes': price_or_None, 'no': price_or_None} для бинарного рынка Opinion.
    Берём лучшую ASK цену (самую дешёвую продажу).
    """
    detail = client.get_market(market_id)
    if detail.errno != 0:
        raise Exception(f"Opinion get_market error {detail.errno}: {detail.errmsg}")

    m = detail.result.data

    yes_token_id = getattr(m, "yes_token_id", None)
    no_token_id = getattr(m, "no_token_id", None)

    if not yes_token_id or not no_token_id:
        # Если структура другая — вернём N/A, а в дебаге это увидим
        return {"yes": None, "no": None}

    # ---- YES ----
    price_yes: Optional[float] = None
    book_yes = _get_orderbook_core(yes_token_id)
    if book_yes is not None:
        price_yes = _extract_best_ask_price(book_yes)

    # ---- NO ----
    price_no: Optional[float] = None
    book_no = _get_orderbook_core(no_token_id)
    if book_no is not None:
        price_no = _extract_best_ask_price(book_no)

    return {"yes": price_yes, "no": price_no}
