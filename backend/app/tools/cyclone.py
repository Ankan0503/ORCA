"""Cyclone watch, from IMD's own Tropical Weather Outlook.

ORCA could warn about lightning but knew nothing about cyclones — the single
largest gap for a problem filed under disaster management. This closes it using
the authority that actually declares cyclones in this ocean: RSMC Tropical
Cyclones, New Delhi, which is IMD's Regional Specialised Meteorological Centre
for the whole North Indian Ocean.

ORCA never decides that a cyclone exists. A cyclone is a declaration, not a
measurement, and inventing one from wind fields would be exactly the kind of
borrowed authority this project refuses. Everything here is read from what RSMC
published.

Two things are extracted, and the second is the more useful:

- **Systems present now** — low pressure areas, depressions, cyclonic storms,
  with the region each lies over.
- **Probability of cyclogenesis for the next 168 hours**, in seven 24-hour
  steps, per basin. This is IMD's own forward-looking judgement of whether a
  storm will *form*, which is what gives a fisherman days of warning rather
  than hours. Its scale is published on the bulletin itself: NIL 0%, LOW 1-33%,
  MODERATE 34-66%, HIGH 67-100%.

Discovery is deliberately indirect. The outlook PDF's URL contains a hash and a
date and changes daily, so it cannot be hardcoded; the RSMC homepage is the
stable entry point and the current document is found by reading its links. That
also reveals the quiet-day state directly, because on a calm day IMD points its
National Bulletin link at a file literally named "No_Cyclone.pdf".
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import date

import httpx

RSMC_HOME = "https://rsmcnewdelhi.imd.gov.in/"
USER_AGENT = "ORCA-Marine/0.1 (SIH 26176 marine advisory prototype)"

# The outlook is issued once a day, so caching for hours is accurate rather than
# merely convenient. Keyed by date so a new day always refetches.
_CACHE_TTL_SECONDS = 3 * 3600
_cache: dict[str, tuple[float, "CycloneOutlook"]] = {}

# IMD's published scale for the cyclogenesis table, quoted on every bulletin.
PROBABILITY_SCALE = {
    "NIL": "0%",
    "LOW": "1-33%",
    "MODERATE": "34-66%",
    "HIGH": "67-100%",
}

# The seven forecast steps the outlook table always carries.
FORECAST_STEPS = (
    "24 hours",
    "24-48 hours",
    "48-72 hours",
    "72-96 hours",
    "96-120 hours",
    "120-144 hours",
    "144-168 hours",
)

# System types in ascending severity, as IMD names them. Matched against the
# bulletin narrative to report what is actually out there.
SYSTEM_TYPES = (
    ("super cyclonic storm", 7),
    ("extremely severe cyclonic storm", 6),
    ("very severe cyclonic storm", 5),
    ("severe cyclonic storm", 4),
    ("cyclonic storm", 3),
    ("deep depression", 2),
    ("depression", 1),
    ("well marked low pressure", 0),
    ("low pressure area", 0),
)


class CycloneDataError(RuntimeError):
    """Raised when the RSMC outlook cannot be reached or read."""


@dataclass
class BasinOutlook:
    """One ocean basin's section of the outlook."""

    basin: str  # "Bay of Bengal" | "Arabian Sea"
    narrative: str
    # Seven cyclogenesis probabilities, aligned with FORECAST_STEPS.
    cyclogenesis: list[str] = field(default_factory=list)

    @property
    def peak_probability(self) -> str:
        """The strongest formation probability anywhere in the next 7 days."""
        order = ["NIL", "LOW", "MODERATE", "HIGH"]
        found = [p for p in self.cyclogenesis if p in order]
        return max(found, key=order.index) if found else "UNKNOWN"

    @property
    def first_risk_step(self) -> str | None:
        """The earliest window where formation is more than NIL."""
        for step, value in zip(FORECAST_STEPS, self.cyclogenesis):
            if value not in ("NIL", ""):
                return step
        return None

    def to_dict(self) -> dict:
        return {
            "basin": self.basin,
            "narrative": self.narrative,
            "cyclogenesis": [
                {"window": step, "probability": value, "meaning": PROBABILITY_SCALE.get(value, "")}
                for step, value in zip(FORECAST_STEPS, self.cyclogenesis)
            ],
            "peakProbability": self.peak_probability,
            "firstRiskWindow": self.first_risk_step,
        }


@dataclass
class WeatherSystem:
    """A system RSMC says is present, as it named it."""

    kind: str  # e.g. "low pressure area", "depression", "cyclonic storm"
    severity: int  # 0 low pressure .. 7 super cyclonic storm
    basin: str
    sentence: str  # the bulletin's own wording, kept verbatim

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "severity": self.severity,
            "basin": self.basin,
            "sentence": self.sentence,
        }


@dataclass
class CycloneOutlook:
    """IMD's tropical weather outlook for the North Indian Ocean."""

    issued_text: str | None
    source_url: str
    basins: list[BasinOutlook] = field(default_factory=list)
    systems: list[WeatherSystem] = field(default_factory=list)
    # True when IMD is publishing its explicit "No Cyclone" bulletin.
    no_cyclone_declared: bool = False
    stale: bool = False

    def basin_for(self, longitude: float) -> BasinOutlook | None:
        """The basin a position sits in.

        India's southern tip is near 77E; everything east of roughly 80E drains
        into the Bay of Bengal and everything west into the Arabian Sea. The
        Andamans sit well east and are covered by the Bay of Bengal outlook,
        which is how IMD groups them too.
        """
        wanted = "Bay of Bengal" if longitude >= 80.0 else "Arabian Sea"
        for basin in self.basins:
            if basin.basin == wanted:
                return basin
        return self.basins[0] if self.basins else None

    @property
    def active_cyclone(self) -> WeatherSystem | None:
        """The most severe system at cyclonic-storm strength or above."""
        storms = [s for s in self.systems if s.severity >= 3]
        return max(storms, key=lambda s: s.severity) if storms else None

    def to_dict(self) -> dict:
        return {
            "issued": self.issued_text,
            "sourceUrl": self.source_url,
            "source": "IMD / RSMC Tropical Cyclones, New Delhi — Tropical Weather Outlook",
            "noCycloneDeclared": self.no_cyclone_declared,
            "stale": self.stale,
            "basins": [b.to_dict() for b in self.basins],
            "systems": [s.to_dict() for s in self.systems],
            "activeCyclone": self.active_cyclone.to_dict() if self.active_cyclone else None,
        }


# --- Parsing -----------------------------------------------------------------


def parse_probabilities(text: str, after: int) -> list[str]:
    """Read one cyclogenesis table following a position in the text.

    The PDF flattens the table into a header row of window names followed by a
    row of seven values, so the values are the seven scale words after the last
    header cell ("144-168 HOURS").

    Anchoring on that header matters. Every page of the bulletin carries a
    footer explaining the scale — "NIL:0%, LOW:1-33%, MODERATE:34-66% and
    HIGH:67-100%" — and a naive scan of the text after the heading reads that
    legend as data, turning a bulletin that says NIL into a claim of HIGH
    cyclone formation probability. Scale words followed by a colon or a
    percentage are therefore rejected outright as a second guard.
    """
    window = text[after : after + 1600]

    anchor = re.search(r"144\s*-\s*168\s*HOURS", window, re.IGNORECASE)
    if anchor:
        window = window[anchor.end() :]

    # A bare word is data; "NIL:0%" or "LOW:1-33%" is the footnote defining it.
    words = re.findall(r"\b(NIL|LOW|MODERATE|HIGH)\b(?!\s*[:%])", window)
    return words[:7]


def parse_systems(narrative: str, basin: str) -> list[WeatherSystem]:
    """Pick out the systems a basin's narrative describes.

    Sentences are matched against IMD's own vocabulary, strongest first, so a
    "deep depression" is not also counted as a "depression". Only sentences that
    assert presence are kept: the bulletin often notes that yesterday's system
    "became less marked", which is the opposite of a warning.
    """
    found: list[WeatherSystem] = []
    for sentence in re.split(r"(?<=[.])\s+", narrative):
        lowered = sentence.lower()
        if not lowered.strip():
            continue
        # A system that has weakened away is not a present hazard.
        if "less marked" in lowered or "weakened into" in lowered:
            continue
        for kind, severity in SYSTEM_TYPES:
            if kind in lowered:
                found.append(
                    WeatherSystem(
                        kind=kind,
                        severity=severity,
                        basin=basin,
                        sentence=re.sub(r"\s+", " ", sentence).strip()[:400],
                    )
                )
                break
    return found


def parse_outlook(text: str, source_url: str) -> CycloneOutlook:
    """Turn the outlook PDF's text into structured findings."""
    flat = re.sub(r"[ \t]+", " ", text)

    issued = None
    match = re.search(
        r"VALID FOR THE NEXT \d+ HOURS ISSUED AT ([^.]{0,60}?\d{2}\.\d{2}\.\d{4})",
        flat,
        re.IGNORECASE,
    )
    if match:
        issued = re.sub(r"\s+", " ", match.group(1)).strip()
    else:
        match = re.search(r"DATED\s+(\d{2}\.\d{2}\.\d{4})", flat, re.IGNORECASE)
        issued = match.group(1) if match else None

    basins: list[BasinOutlook] = []
    systems: list[WeatherSystem] = []

    # Each basin's section runs from its heading to the next heading.
    headings = [
        ("Bay of Bengal", re.search(r"BAY OF BENGAL\s*:", flat, re.IGNORECASE)),
        ("Arabian Sea", re.search(r"ARABIAN SEA\s*:", flat, re.IGNORECASE)),
    ]
    positions = [(name, m.start()) for name, m in headings if m]
    positions.sort(key=lambda pair: pair[1])

    for index, (name, start) in enumerate(positions):
        end = positions[index + 1][1] if index + 1 < len(positions) else len(flat)
        section = flat[start:end]

        # The narrative is the prose before the cyclogenesis table.
        table_at = re.search(r"PROBABILITY OF CYCLOGENESIS", section, re.IGNORECASE)
        narrative = section[: table_at.start()] if table_at else section
        narrative = re.sub(r"\s+", " ", narrative).strip()

        probabilities = (
            parse_probabilities(section, table_at.start()) if table_at else []
        )
        basins.append(
            BasinOutlook(basin=name, narrative=narrative, cyclogenesis=probabilities)
        )
        systems.extend(parse_systems(narrative, name))

    return CycloneOutlook(
        issued_text=issued,
        source_url=source_url,
        basins=basins,
        systems=systems,
    )


# --- Fetching ----------------------------------------------------------------


def _extract_links(html: str) -> dict[str, str]:
    """Map link text to href for the RSMC homepage's product links."""
    links: dict[str, str] = {}
    for match in re.finditer(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL
    ):
        href, label = match.group(1), re.sub(r"<[^>]+>", " ", match.group(2))
        label = re.sub(r"\s+", " ", label).strip()
        if label:
            links.setdefault(label, href)
    return links


def _newest_outlook(links: dict[str, str]) -> str | None:
    """The most recent Tropical Weather Outlook PDF among the homepage's links.

    The homepage carries several outlook links — the current one appears more
    than once, and older copies linger elsewhere on the page. Picking the first
    match by document order silently returned a bulletin over a year stale, so
    the date is read out of each filename and the newest wins. A candidate whose
    filename carries no date loses to any that does.
    """
    candidates: list[tuple[tuple[int, int, int], str]] = []
    for label, href in links.items():
        haystack = f"{label} {href}".lower().replace("_", " ").replace("%20", " ")
        if "tropical weather outlook" not in haystack:
            continue
        if not href.lower().endswith(".pdf") or "no cyclone" in haystack:
            continue
        match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", href)
        stamp = (
            (int(match.group(3)), int(match.group(2)), int(match.group(1)))
            if match
            else (0, 0, 0)
        )
        candidates.append((stamp, href))

    if not candidates:
        return None
    return max(candidates, key=lambda pair: pair[0])[1]


def _absolute(href: str) -> str:
    if href.startswith("http"):
        return href
    return RSMC_HOME.rstrip("/") + "/" + href.lstrip("/")


async def fetch_outlook(*, timeout: float = 60.0, force: bool = False) -> CycloneOutlook:
    """Today's tropical weather outlook, discovered from the RSMC homepage."""
    key = date.today().isoformat()
    hit = _cache.get(key)
    if hit and not force and (time.monotonic() - hit[0]) < _CACHE_TTL_SECONDS:
        return hit[1]

    headers = {"User-Agent": USER_AGENT}
    try:
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, headers=headers
        ) as client:
            home = await client.get(RSMC_HOME)
            if home.status_code >= 400:
                raise CycloneDataError(f"RSMC homepage failed ({home.status_code})")

            links = _extract_links(home.text)

            # IMD points these at a file named "No_Cyclone.pdf" on a quiet day,
            # which is the clearest possible statement of the quiet case.
            no_cyclone = any(
                "no_cyclone" in href.lower()
                for label, href in links.items()
                if "bulletin" in label.lower() or "outlook" in label.lower()
            )

            outlook_href = _newest_outlook(links)
            if outlook_href is None:
                raise CycloneDataError("No Tropical Weather Outlook link on the RSMC homepage")

            url = _absolute(outlook_href)
            pdf = await client.get(url)
            if pdf.status_code >= 400:
                raise CycloneDataError(f"Outlook PDF failed ({pdf.status_code})")
    except httpx.HTTPError as exc:
        raise CycloneDataError(f"Could not reach RSMC: {exc}") from exc

    text = _pdf_text(pdf.content)
    outlook = parse_outlook(text, url)
    outlook.no_cyclone_declared = no_cyclone

    _cache[key] = (time.monotonic(), outlook)
    return outlook


def _pdf_text(data: bytes) -> str:
    """Extract text from the outlook PDF."""
    try:
        import io

        import pypdf
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise CycloneDataError("pypdf is required to read the RSMC outlook") from exc

    try:
        reader = pypdf.PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:  # noqa: BLE001 - any malformed PDF is a data error
        raise CycloneDataError(f"Could not read the outlook PDF: {exc}") from exc
