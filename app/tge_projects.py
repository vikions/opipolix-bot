import re
from dataclasses import dataclass
from typing import List, Optional

try:
    from opinion_tracked_markets import WHITELIST_CHILD_IDS, CHILD_TO_PROJECT
except Exception:
    WHITELIST_CHILD_IDS = []
    CHILD_TO_PROJECT = {}


FALLBACK_PROJECTS = ["Base", "MetaMask"]

DISCORD_PROJECTS = {
    "Base": {
        "discord_channel_id": "1072952844161916938",
        "discord_server_id": "1067165013397213286",
        "discord_channel_name": "base-announcements",
    },
    "Opinion": {
        "discord_channel_id": "1263696463553105981",
        "discord_server_id": "1254615232496533545",
        "discord_channel_name": "accounts",
    },
}


@dataclass(frozen=True)
class TgeProjectConfig:
    name: str
    key: str
    discord_channel_id: Optional[str]
    discord_server_id: Optional[str]
    discord_channel_name: Optional[str]


def _project_key(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return cleaned.upper()


def list_project_names() -> List[str]:
    names = []
    for market_id in WHITELIST_CHILD_IDS:
        name = CHILD_TO_PROJECT.get(market_id)
        if not name:
            continue
        if name not in names:
            names.append(name)

    if not names:
        names.extend(FALLBACK_PROJECTS)

    for extra in ("Base", "Opinion"):
        if extra not in names:
            names.append(extra)

    return names


def match_project_name(text: str) -> Optional[str]:
    if not text:
        return None
    text_clean = text.strip().lower()
    for name in list_project_names():
        if name.lower() == text_clean:
            return name
    return None


def get_project_config(project_name: str) -> Optional[TgeProjectConfig]:
    if not project_name:
        return None
    key = _project_key(project_name)
    config = DISCORD_PROJECTS.get(project_name)
    if config:
        return TgeProjectConfig(name=project_name, key=key, **config)

    return TgeProjectConfig(
        name=project_name,
        key=key,
        discord_channel_id=None,
        discord_server_id=None,
        discord_channel_name=None,
    )
