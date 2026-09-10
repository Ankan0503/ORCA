"""Translate a response's prose into the caller's language, at request time.

Why this exists
---------------
ORCA composes its verdicts in Python — "Severe risk — do not go. Sea is unsafe:
thunderstorms with lightning from 09:00" — and returned them in English whatever
the `lang` parameter said. The parameter was accepted and used only to pick the
right PFZ advisory; the sentence itself never changed. A fisherman with the app
set to Bengali got Bengali labels around an English verdict, which is the half
that actually matters.

The trade this makes, stated plainly
------------------------------------
Translating here means a network call on the request path, and it means the
prose falls back to English when there is no connectivity. That is a real cost
for a user at the edge of coverage, and the alternative — composing sentences
from per-language fragments held on the server — would work offline. The
project chose request-time translation deliberately, for the reach it gives
across every phrasing without enumerating them first. It is recorded in
LIMITATIONS.md so the trade is visible rather than assumed.

Three things make it survivable:

**A cache.** ORCA's phrasings repeat heavily — there are only so many ways it
says "do not go" — so after warm-up most requests translate nothing at all. The
cache is keyed on the exact text and language, so a sentence differing only in
its numbers is still a miss; masking (below) is what collapses those into one.

**Masking.** Numbers, times, units, bearings, agency names and the brand are
replaced with markers before translation and restored after. Without it Sarvam
turned "~40-45 mins at 8 knots" into "8 notes per second" while translating the
UI strings. It also means "visibility drops to 1920 m" and "…to 1250 m" share a
cache entry.

**Failing open.** A translation that cannot be fetched returns the English. A
missing translation is a degraded answer; a failed request is no answer, and the
verdict is the thing the user came for.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from ..providers.sarvam import SarvamClient, SarvamError
from .detect import SUPPORTED_LANGUAGES, to_sarvam_code

log = logging.getLogger("orca.localise")

# Keys whose values are prose meant for a person to read. Everything else in a
# response — identifiers, codes, ISO timestamps, units on their own — is left
# alone. An allowlist rather than a blocklist: a new field is English until
# somebody decides it is prose, which is the safer direction to be wrong in.
PROSE_KEYS = frozenset(
    {
        "summary", "headline", "detail", "message", "note", "rationale",
        "advice", "description", "label", "warning", "reason", "text",
        "scope", "sentence", "verdict", "recommendation", "value",
        # List-valued prose. A list's items inherit the list's own key, so these
        # are the names of arrays of sentences rather than of single strings —
        # `drivers` is why "sea is unsafe: thunderstorms..." stayed English in
        # the first pass while the summary quoting it did not.
        "drivers", "reasons", "warnings", "advisories", "explanations",
        "actionableAdvisories", "nextActions", "factors", "steps", "notes",
    }
)

# Keys that look like prose and are not. `source` names an agency and must read
# the same in every language — "Open-Meteo Marine + Forecast API" translated
# into Bengali is no longer a citation anybody can follow.
NEVER_KEYS = frozenset({"source", "sourceUrl", "url", "id", "code", "secid", "kind"})

# Below this a string is a label, a unit or a fragment; translating it costs a
# call and usually returns it unchanged.
MIN_CHARS = 12

# Spans a translator must not see. Same list as the UI-string generator, for the
# same reason: it mangled every one of these when it could read them.
_PROTECT = [
    re.compile(r"\bORCA\b"),
    re.compile(r"\bINCOIS\b|\bIMD\b|\bRSMC\b|\bPFZ\b|\bNOAA\b|\bEEZ\b|\bERA5\b"),
    re.compile(r"\b\d{1,2}:\d{2}\b"),                       # clock times
    re.compile(r"\d+(?:\.\d+)?\s*°"),                       # bearings
    re.compile(
        r"~?\d+(?:[.,]\d+)?(?:\s*[–-]\s*\d+(?:[.,]\d+)?)?\s*"
        r"(?:km/h|km|m/s|m|kts?|knots?|mins?|minutes?|hrs?|hours?|h|mm|%)\b",
        re.I,
    ),
    re.compile(r"\b\d{1,2}\s+[A-Z]{3}\s+\d{4}\b"),          # 9 SEP 2026
]

_MARK = "@@{}@@"
_MARK_RE = re.compile(r"@\s*@\s*(\d+)\s*@\s*@")

_cache: dict[tuple[str, str], str] = {}
# Bounded so a long-running process cannot grow without limit. ORCA's phrasings
# are few enough that this is generous; when it fills, it is cleared rather than
# evicted one by one, because the cost of a cold cache here is one extra call.
_CACHE_LIMIT = 4000


def _mask(text: str) -> tuple[str, list[str]]:
    saved: list[str] = []
    out = text
    for pattern in _PROTECT:
        while True:
            match = pattern.search(out)
            if not match:
                break
            token = _MARK.format(len(saved))
            saved.append(match.group(0))
            out = out[: match.start()] + token + out[match.end() :]
    return out, saved


def _unmask(text: str, saved: list[str]) -> str:
    def restore(match: re.Match) -> str:
        index = int(match.group(1))
        return saved[index] if index < len(saved) else match.group(0)

    return _MARK_RE.sub(restore, text)


def _translatable(key: str, value: Any) -> bool:
    if key in NEVER_KEYS or not isinstance(value, str):
        return False
    text = value.strip()
    if len(text) < MIN_CHARS or not re.search(r"[A-Za-z]{3}", text):
        return False
    return key in PROSE_KEYS


def collect(node: Any, out: set, key: str = "") -> None:
    """Every distinct prose string in a payload."""
    if isinstance(node, dict):
        for k, v in node.items():
            collect(v, out, k)
    elif isinstance(node, list):
        for item in node:
            collect(item, out, key)
    elif _translatable(key, node):
        out.add(node.strip())


def apply(node: Any, table: dict[str, str], key: str = "") -> Any:
    """Rebuild a payload with translated prose swapped in."""
    if isinstance(node, dict):
        return {k: apply(v, table, k) for k, v in node.items()}
    if isinstance(node, list):
        return [apply(item, table, key) for item in node]
    if _translatable(key, node):
        return table.get(node.strip(), node)
    return node


async def _one(client: SarvamClient, text: str, language: str, sem: asyncio.Semaphore,
               table: dict[str, str]) -> None:
    masked, saved = _mask(text)
    # Nothing left but protected spans — a bearing, a time, an agency name.
    if not re.search(r"[A-Za-z]{3}", _MARK_RE.sub("", masked)):
        table[text] = text
        return

    key = (masked, language)
    hit = _cache.get(key)
    if hit is not None:
        table[text] = _unmask(hit, saved)
        return

    async with sem:
        try:
            got = await client.translate(
                text=masked,
                target_language_code=to_sarvam_code(language),
                source_language_code="en-IN",
            )
        except SarvamError as exc:
            log.warning("localise: %s", exc)
            table[text] = text  # fail open
            return

    if got:
        if len(_cache) >= _CACHE_LIMIT:
            _cache.clear()
        _cache[key] = got
        table[text] = _unmask(got, saved)
    else:
        table[text] = text


async def localise(payload: Any, language: str, sarvam: SarvamClient,
                   concurrency: int = 6) -> Any:
    """Return the payload with its prose in `language`.

    English, an unknown language, or a payload with no prose all short-circuit
    without touching the network.
    """
    if not language or language == "en" or language not in SUPPORTED_LANGUAGES:
        return payload

    strings: set = set()
    collect(payload, strings)
    if not strings:
        return payload

    table: dict[str, str] = {}
    sem = asyncio.Semaphore(concurrency)
    await asyncio.gather(*(_one(sarvam, s, language, sem, table) for s in strings))
    return apply(payload, table)


def cache_stats() -> dict:
    return {"entries": len(_cache), "limit": _CACHE_LIMIT}
