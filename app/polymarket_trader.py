# app/polymarket_trader.py

import os
import json
import logging
from urllib.parse import urlparse

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import MarketOrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

from .poly_builder_signing import (
    BuilderConfig,
    BuilderApiKeyCreds,
    BuilderHeaderPayload,
)

logger = logging.getLogger(__name__)

# --- ENV VARS ---

POLY_CLOB_HOST = os.getenv("POLY_CLOB_HOST", "https://clob.polymarket.com")
POLY_CHAIN_ID = int(os.getenv("POLY_CHAIN_ID", "137"))

POLY_PK = os.getenv("POLY_PK")          # private key of trader wallet
POLY_FUNDER = os.getenv("POLY_FUNDER")  # address that holds funds (usually same EOA)

# Builder creds (for attribution)
POLY_BUILDER_API_KEY = os.getenv("POLY_BUILDER_API_KEY")
POLY_BUILDER_SECRET = os.getenv("POLY_BUILDER_SECRET")
POLY_BUILDER_PASSPHRASE = os.getenv("POLY_BUILDER_PASSPHRASE")

# YES-tokenIDs
POLY_TOKEN_METAMASK_YES = os.getenv("POLY_TOKEN_METAMASK_YES")
POLY_TOKEN_BASE_YES = os.getenv("POLY_TOKEN_BASE_YES")


if not POLY_PK or not POLY_FUNDER:
    raise RuntimeError("POLY_PK and POLY_FUNDER must be set in environment")

if not (POLY_BUILDER_API_KEY and POLY_BUILDER_SECRET and POLY_BUILDER_PASSPHRASE):
    raise RuntimeError("Builder creds (POLY_BUILDER_API_KEY/SECRET/PASSPHRASE) must be set")


def _make_builder_config() -> BuilderConfig:
    creds = BuilderApiKeyCreds(
        key=POLY_BUILDER_API_KEY,
        secret=POLY_BUILDER_SECRET,
        passphrase=POLY_BUILDER_PASSPHRASE,
    )
    return BuilderConfig(local_builder_creds=creds)


def _wrap_session_with_builder(session, builder_config: BuilderConfig):
    """
    Monkey-patch requests.Session.request to automatically inject
    builder headers into EVERY HTTP request to the CLOB.

    Так мы получаем POLY_BUILDER_* хедеры на всех запросах,
    как требует Order Attribution.
    """
    original_request = session.request

    def wrapped(method, url, **kwargs):
        headers = kwargs.get("headers") or {}

        # Нормализуем body → строка JSON, как реально уходит на сервер
        body_str = ""
        if "json" in kwargs and kwargs["json"] is not None:
            body_str = json.dumps(kwargs["json"], separators=(",", ":"), sort_keys=True)
            kwargs["data"] = body_str
            kwargs.pop("json", None)
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
        elif "data" in kwargs and kwargs["data"] is not None:
            data = kwargs["data"]
            if isinstance(data, (bytes, bytearray)):
                body_str = data.decode("utf-8")
            else:
                body_str = str(data)
        else:
            body_str = ""

        path = urlparse(url).path

        try:
            payload = builder_config.generate_builder_headers(
                method.upper(),
                path,
                body_str,
            )
            if isinstance(payload, BuilderHeaderPayload):
                headers.update(payload.to_dict())
            elif isinstance(payload, dict):
                headers.update(payload)
        except Exception as e:
            logger.warning("Failed to generate builder headers: %s", e)

        kwargs["headers"] = headers
        return original_request(method, url, **kwargs)

    session.request = wrapped


def _create_client() -> ClobClient:
    """
    Create ClobClient with:
    - POLY_PK (EOA private key)
    - POLY_FUNDER (address with funds)
    - L2 API creds
    - builder attribution via local signing
    """
    client = ClobClient(
        POLY_CLOB_HOST,
        key=POLY_PK,
        chain_id=POLY_CHAIN_ID,
        signature_type=0,  # 0 = regular EOA
        funder=POLY_FUNDER,
    )

    # L2 API creds – обязательно для торговли
    client.set_api_creds(client.create_or_derive_api_creds())

    # BuilderConfig для локальной подписи
    builder_config = _make_builder_config()

    # Monkey-patch HTTP session, чтобы добавлять POLY_BUILDER_* headers
    if hasattr(client, "session"):
        _wrap_session_with_builder(client.session, builder_config)
    else:
        logger.warning("ClobClient has no 'session' attribute – builder headers may not be attached")

    return client


_client = _create_client()


def _resolve_yes_token_id(alias: str) -> str:
    alias = alias.lower()
    if alias == "metamask":
        token = POLY_TOKEN_METAMASK_YES
        if not token or token.startswith("<") or token.strip() == "":
            raise RuntimeError("POLY_TOKEN_METAMASK_YES is not set correctly")
        return token
    elif alias == "base":
        token = POLY_TOKEN_BASE_YES
        if not token or token.startswith("<") or token.strip() == "":
            raise RuntimeError("POLY_TOKEN_BASE_YES is not set correctly")
        return token
    else:
        raise ValueError(f"Unsupported alias '{alias}'. Use 'metamask' or 'base'.")


def place_yes_market_order(alias: str, usd_amount: float):
    """
    Place MARKET BUY YES order with builder attribution.

    :param alias: 'metamask' | 'base'
    :param usd_amount: notional in USDC
    """
    if usd_amount <= 0:
        raise ValueError("usd_amount must be > 0")

    token_id = _resolve_yes_token_id(alias)

    mo = MarketOrderArgs(
        token_id=token_id,
        amount=float(usd_amount),
        side=BUY,
        order_type=OrderType.FOK,
    )

    signed = _client.create_market_order(mo)
    resp = _client.post_order(signed, OrderType.FOK)
    return resp
