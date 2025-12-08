# app/poly_builder_signing.py
"""
Minimal, local version of Polymarket builder signing SDK.

Based on:
- config.py
- sdk_types.py
- signer.py
from https://github.com/Polymarket/py-builder-signing-sdk

We only implement LOCAL signing (BuilderApiKeyCreds + BuilderConfig + BuilderSigner),
enough to generate POLY_BUILDER_* headers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict
import time
import hmac
import hashlib


# ====== Types (sdk_types.py) ======

@dataclass
class BuilderApiKeyCreds:
    key: str
    secret: str
    passphrase: str


class BuilderType(Enum):
    UNAVAILABLE = "UNAVAILABLE"
    LOCAL = "LOCAL"
    REMOTE = "REMOTE"


@dataclass
class BuilderHeaderPayload:
    """Builder header payload"""

    POLY_BUILDER_API_KEY: str
    POLY_BUILDER_TIMESTAMP: str
    POLY_BUILDER_PASSPHRASE: str
    POLY_BUILDER_SIGNATURE: str

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for use as headers"""
        return {
            "POLY_BUILDER_API_KEY": self.POLY_BUILDER_API_KEY,
            "POLY_BUILDER_TIMESTAMP": self.POLY_BUILDER_TIMESTAMP,
            "POLY_BUILDER_PASSPHRASE": self.POLY_BUILDER_PASSPHRASE,
            "POLY_BUILDER_SIGNATURE": self.POLY_BUILDER_SIGNATURE,
        }


# ====== HMAC signing (signing/hmac.py, воспроизводим логику) ======

def build_hmac_signature(
    secret: str,
    timestamp: str,
    method: str,
    path: str,
    body: Optional[str] = None,
) -> str:
    """
    Build HMAC signature for builder headers.

    Typical pattern (как в JS/TS клиентах Polymarket):
    message = timestamp + method + path + (body or "")
    signature = HMAC_SHA256(secret, message)

    :return: hex string
    """
    method_up = (method or "").upper()
    msg = f"{timestamp}{method_up}{path}{body or ''}"
    msg_bytes = msg.encode("utf-8")
    key_bytes = secret.encode("utf-8")
    sig = hmac.new(key_bytes, msg_bytes, hashlib.sha256).hexdigest()
    return sig


# ====== Signer (signer.py) ======

class BuilderSigner:
    def __init__(self, creds: BuilderApiKeyCreds):
        self.creds = creds

    def create_builder_header_payload(
        self,
        method: str,
        path: str,
        body: Optional[str] = None,
        timestamp: Optional[int] = None,
    ) -> BuilderHeaderPayload:
        """
        Creates a builder header payload.

        Args:
            method: HTTP method
            path: Request path
            body: Optional request body (raw JSON string)
            timestamp: Optional timestamp (defaults to current time, seconds)

        Returns:
            BuilderHeaderPayload
        """
        ts_int = int(time.time()) if timestamp is None else int(timestamp)
        ts_str = str(ts_int)

        builder_sig = build_hmac_signature(
            self.creds.secret,
            ts_str,
            method,
            path,
            body,
        )

        return BuilderHeaderPayload(
            POLY_BUILDER_API_KEY=self.creds.key,
            POLY_BUILDER_PASSPHRASE=self.creds.passphrase,
            POLY_BUILDER_SIGNATURE=builder_sig,
            POLY_BUILDER_TIMESTAMP=ts_str,
        )


# ====== Config (config.py, урезанная версия: только LOCAL) ======

class BuilderConfig:
    """
    Configuration handler for builder signing/authentication.

    В этой минимальной версии мы поддерживаем ТОЛЬКО локальную подпись
    через BuilderApiKeyCreds (LOCAL). Remote builder тут не нужен.
    """

    def __init__(
        self,
        *,
        local_builder_creds: Optional[BuilderApiKeyCreds] = None,
    ) -> None:
        self.local_builder_creds: Optional[BuilderApiKeyCreds] = None
        self.signer: Optional[BuilderSigner] = None

        if local_builder_creds is not None:
            if not self._has_valid_local_creds(local_builder_creds):
                raise ValueError("invalid local builder credentials!")
            self.local_builder_creds = local_builder_creds
            self.signer = BuilderSigner(local_builder_creds)

    def generate_builder_headers(
        self,
        method: str,
        path: str,
        body: Optional[str] = None,
        timestamp: Optional[int] = None,
    ) -> Optional[BuilderHeaderPayload]:
        """
        Generate signed builder headers using local credentials.
        """
        self._ensure_valid()
        builder_type = self.get_builder_type()

        if builder_type == BuilderType.LOCAL and self.signer is not None:
            return self.signer.create_builder_header_payload(
                method, path, body, timestamp
            )

        return None

    def is_valid(self) -> bool:
        return self.get_builder_type() != BuilderType.UNAVAILABLE

    def get_builder_type(self) -> BuilderType:
        if self.local_builder_creds:
            return BuilderType.LOCAL
        return BuilderType.UNAVAILABLE

    @staticmethod
    def _has_valid_local_creds(creds: Optional[BuilderApiKeyCreds]) -> bool:
        if creds is None:
            return False
        if not (creds.key.strip()):
            return False
        if not (creds.secret.strip()):
            return False
        if not (creds.passphrase.strip()):
            return False
        return True

    def _ensure_valid(self) -> None:
        if self.get_builder_type() == BuilderType.UNAVAILABLE:
            raise ValueError("invalid builder creds configured!")
