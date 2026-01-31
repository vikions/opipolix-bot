import hashlib
import html
import re
from datetime import datetime
from typing import Dict, List, Optional


MAX_ALIAS_LEN = 5
MAX_LINE_LEN = 32

KNOWN_ALIAS_BY_ALIAS = {
    "opensea": "OpenS",
    "opinion": "Opin",
    "metamask": "MetaM",
    "base": "Base",
    "abstract": "Abst",
    "polymarket": "PolyM",
}

KNOWN_ALIAS_BY_TITLE = {
    "opensea token by march 31, 2026": "OpenS",
    "opinion token by february 17, 2026": "Opin",
    "metamask token by june 30": "MetaM",
    "base token by june 30, 2026": "Base",
    "abstract token by dec 31, 2026": "Abst",
    "polymarket token by march 31, 2026": "PolyM",
}


def _normalize_title(title: str) -> str:
    return " ".join(title.lower().split())


def short_market_title(title: str) -> str:
    if not title:
        return "Market"
    cleaned = title.strip()
    if " by " in cleaned:
        cleaned = cleaned.split(" by ", 1)[0].strip()
    if " one day after " in cleaned:
        cleaned = cleaned.split(" one day after ", 1)[0].strip()
    if cleaned.endswith("?"):
        cleaned = cleaned[:-1].strip()
    if len(cleaned) > 40:
        cleaned = f"{cleaned[:37].rstrip()}..."
    return cleaned


def format_percent(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if numeric < 0:
        numeric = 0.0
    if numeric > 1:
        percent = numeric
    else:
        percent = numeric * 100

    if abs(percent - round(percent)) < 0.05:
        return f"{int(round(percent))}%"
    return f"{percent:.1f}%"


def _known_alias(snapshot: Dict[str, object]) -> Optional[str]:
    alias = snapshot.get("alias")
    if isinstance(alias, str) and alias.lower() in KNOWN_ALIAS_BY_ALIAS:
        return KNOWN_ALIAS_BY_ALIAS[alias.lower()]
    name = snapshot.get("name")
    if isinstance(name, str):
        normalized = _normalize_title(name)
        if normalized in KNOWN_ALIAS_BY_TITLE:
            return KNOWN_ALIAS_BY_TITLE[normalized]
        if "opensea token" in normalized:
            return "OpenS"
        if "opinion token" in normalized:
            return "Opin"
        if "metamask token" in normalized:
            return "MetaM"
        if normalized.startswith("base token"):
            return "Base"
        if "abstract token" in normalized:
            return "Abst"
        if "polymarket token" in normalized:
            return "PolyM"
    return None


def _auto_alias_from_name(name: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", name or "")
    if not words:
        return "Mkt"

    if len(words) >= 2:
        initials = "".join(word[0] for word in words[:3])
        alias = initials.upper()
    else:
        word = words[0]
        alias = word[:MAX_ALIAS_LEN]
        if len(alias) > 1:
            alias = alias[0].upper() + alias[1:].lower()
        else:
            alias = alias.upper()

    if len(alias) > MAX_ALIAS_LEN:
        alias = alias[:MAX_ALIAS_LEN]
    return alias or "Mkt"


def _ensure_unique_aliases(aliases: List[str]) -> List[str]:
    seen = set()
    unique = []
    for alias in aliases:
        candidate = alias or "Mkt"
        if candidate in seen:
            idx = 2
            while True:
                base = candidate[: max(MAX_ALIAS_LEN - 1, 1)]
                proposal = f"{base}{idx}"
                if proposal not in seen:
                    candidate = proposal
                    break
                idx += 1
        candidate = candidate[:MAX_ALIAS_LEN]
        seen.add(candidate)
        unique.append(candidate)
    return unique


def generate_market_aliases(snapshots: List[Dict[str, object]]) -> List[str]:
    aliases: List[str] = []
    for snapshot in snapshots:
        known = _known_alias(snapshot)
        if known:
            aliases.append(known)
            continue
        name = snapshot.get("name") or snapshot.get("alias") or "Market"
        aliases.append(_auto_alias_from_name(str(name)))

    return _ensure_unique_aliases(aliases)


def _compact_line(alias: str, yes_value: Optional[float], no_value: Optional[float]) -> str:
    alias = alias[:MAX_ALIAS_LEN]
    yes_text = format_percent(yes_value)
    no_text = format_percent(no_value)
    line = f"{alias}  Y:{yes_text}  N:{no_text}"
    if len(line) <= MAX_LINE_LEN:
        return line

    while len(alias) > 1 and len(line) > MAX_LINE_LEN:
        alias = alias[:-1]
        line = f"{alias}  Y:{yes_text}  N:{no_text}"

    return line[:MAX_LINE_LEN]


def _compact_lines(snapshots: List[Dict[str, object]]) -> List[str]:
    aliases = generate_market_aliases(snapshots)
    lines: List[str] = []
    for alias, snapshot in zip(aliases, snapshots):
        line = _compact_line(alias, snapshot.get("yes_value"), snapshot.get("no_value"))
        lines.append(line)
    return lines


def _verbose_lines(snapshots: List[Dict[str, object]]) -> List[str]:
    lines: List[str] = []
    for snapshot in snapshots:
        name = snapshot.get("name") or "Market"
        short_name = short_market_title(str(name))
        safe_name = html.escape(short_name)
        yes_value = format_percent(snapshot.get("yes_value"))
        no_value = format_percent(snapshot.get("no_value"))
        lines.append(safe_name)
        lines.append(f"YES: {yes_value} | NO: {no_value}")
    return lines


def render_widget_text(
    snapshots: List[Dict[str, object]], updated_at: datetime, compact_mode: bool = True
) -> str:
    lines: List[str] = []

    if compact_mode:
        lines.extend(_compact_lines(snapshots))
    else:
        lines.extend(_verbose_lines(snapshots))

    time_str = updated_at.strftime("%H:%M")
    lines.append(f"UTC {time_str}")
    return "\n".join(lines)


def compute_render_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_market_hash(
    snapshots: List[Dict[str, object]], compact_mode: bool = True
) -> str:
    lines: List[str] = []
    if compact_mode:
        lines.extend(_compact_lines(snapshots))
    else:
        lines.extend(_verbose_lines(snapshots))
    return compute_render_hash("\n".join(lines))
