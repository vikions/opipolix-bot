from typing import Iterable, List


DEFAULT_TGE_KEYWORDS = [
    "tge",
    "token generation",
    "token launch",
    "airdrop",
    "claim",
    "snapshot",
    "listing",
    "trading",
    "dex",
    "cex",
    "tokenomics",
    "distribution",
]


def normalize_keywords(keywords: Iterable[str]) -> List[str]:
    normalized = []
    seen = set()
    for keyword in keywords or []:
        if keyword is None:
            continue
        cleaned = str(keyword).strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(lowered)
    return normalized


def find_keywords(text: str, keywords: Iterable[str]) -> List[str]:
    if not text:
        return []
    text_lower = text.lower()
    matches = []
    for keyword in normalize_keywords(keywords):
        if keyword in text_lower:
            matches.append(keyword)
    return matches


def format_keywords(keywords: Iterable[str]) -> str:
    items = [f"\"{kw}\"" for kw in keywords or []]
    return ", ".join(items)


def truncate_text(text: str, limit: int = 300) -> str:
    if text is None:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."
