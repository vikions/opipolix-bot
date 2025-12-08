# app/polymarket_trader.py

import os
import json
import logging
from urllib.parse import urlparse

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import MarketOrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

# ⬇️ ВАЖНО: меняем импорт отсюда:
# from py_builder_signing_sdk import BuilderConfig, BuilderApiKeyCreds
# ⬇️ На вот это (через подмодуль):
from py_builder_signing_sdk.builder_config import (
    BuilderConfig,
    BuilderApiKeyCreds,
    RemoteBuilderConfig,  # на будущее, сейчас можно не использовать
)

logger = logging.getLogger(__name__)

# --- ENV VARS ---

POLY_CLOB_HOST = os.getenv("POLY_CLOB_HOST", "https://clob.polymarket.com")
POLY_CHAIN_ID = int(os.getenv("POLY_CHAIN_ID", "137"))

POLY_PK = os.getenv("POLY_PK")          # private key of wallet that has USDC on Polymarket
POLY_FUNDER = os.getenv("POLY_FUNDER")  # address that actually holds funds

# Builder creds (for attribution)
POLY_BUILDER_API_KEY = os.getenv("POLY_BUILDER_API_KEY")
POLY_BUILDER_SECRET = os.getenv("POLY_BUILDER_SECRET")
POLY_BUILDER_PASSPHRASE = os.getenv("POLY_BUILDER_PASSPHRASE")

# Token IDs for YES outcomes (you MUST set them in Railway env!)
POLY_TOKEN_METAMASK_YES = os.getenv("POLY_TOKEN_METAMASK_YES")
POLY_TOKEN_BASE_YES = os.getenv("POLY_TOKEN_BASE_YES")


if not POLY_PK or not POLY_FUNDER:
    raise RuntimeError("POLY_PK and POLY_FUNDER must be set in environment")

if not (POLY_BUILDER_API_KEY and POLY_BUILDER_SECRET and POLY_BUILDER_PASSPHRASE):
    raise RuntimeError("Builder creds (POLY_BUILDER_API_KEY/SECRET/PASSPHRASE) must be set")


def _make_builder_config() -> BuilderConfig:
    """Create BuilderConfig for local signing (attribution)."""
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

    This way, py-clob-client делает всё как обычно,
    а мы просто добавляем POLY_BUILDER_* headers сверху.
    """
    original_request = session.request

    def wrapped(method, url, **kwargs):
        headers = kwargs.get("headers") or {}

        # Determine body as JSON string (exactly what we send)
        body_str = ""
        if "json" in kwargs and kwargs["json"] is not None:
            # We take JSON dict, make canonical string, send as 'data'
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
            builder_headers = builder_config.generate_builder_headers(
                method.upper(),
                path,
                body_str,
            )
            headers.update(builder_headers)
        except Exception as e:
            logger.warning("Failed to generate builder headers: %s", e)

        kwargs["headers"] = headers
        return original_request(method, url, **kwargs)

    session.request = wrapped


def _create_client() -> ClobClient:
    """
    Create a single global ClobClient with:
    - wallet private key (POLY_PK)
    - funder address (POLY_FUNDER)
    - L2 API creds
    - Builder attribution via py-builder-signing-sdk
    """
    client = ClobClient(
        POLY_CLOB_HOST,
        key=POLY_PK,
        chain_id=POLY_CHAIN_ID,
        # signature_type:
        # 0 - regular EOA, 1 - email/Magic, 2 - proxy
        signature_type=0,
        funder=POLY_FUNDER,
    )

    # L2 API creds (required for trading)
    client.set_api_creds(client.create_or_derive_api_creds())

    # Builder config (local signing)
    builder_config = _make_builder_config()

    # Monkey-patch underlying HTTP session to add builder headers
    if hasattr(client, "session"):
        _wrap_session_with_builder(client.session, builder_config)
    else:
        logger.warning("ClobClient has no 'session' attribute – builder headers might not be attached")

    return client


# Single global client
_client = _create_client()


def _resolve_yes_token_id(alias: str) -> str:
    """
    Map alias -> YES tokenId using env vars.
    You MUST fill POLY_TOKEN_METAMASK_YES / POLY_TOKEN_BASE_YES in Railway.
    """
    alias = alias.lower()
    if alias == "metamask":
        token = POLY_TOKEN_METAMASK_YES
        if not token or token.startswith("<"):
            raise RuntimeError("POLY_TOKEN_METAMASK_YES is not set correctly")
        return token
    elif alias == "base":
        token = POLY_TOKEN_BASE_YES
        if not token or token.startswith("<"):
            raise RuntimeError("POLY_TOKEN_BASE_YES is not set correctly")
        return token
    else:
        raise ValueError(f"Unsupported alias '{alias}'. Use 'metamask' or 'base'.")


def place_yes_market_order(alias: str, usd_amount: float):
    """
    Place a MARKET BUY (YES) order for given alias via Polymarket CLOB.

    - Uses py-clob-client to build & sign order
    - Underlying HTTP call gets builder attribution headers automatically
    """
    if usd_amount <= 0:
        raise ValueError("usd_amount must be > 0")

    token_id = _resolve_yes_token_id(alias)

    mo = MarketOrderArgs(
        token_id=token_id,
        amount=float(usd_amount),
        side=BUY,
        order_type=OrderType.FOK,  # Fill-or-kill market order
    )

    signed = _client.create_market_order(mo)
    resp = _client.post_order(signed, OrderType.FOK)

    return resp
