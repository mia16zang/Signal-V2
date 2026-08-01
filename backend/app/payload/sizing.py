"""Market sizing as attributed claims rather than an estimate.

The old field asked the model "how big is this market?". It does not know, and
a model asked for a number will produce one -- so the same query returned
$496.1m at confidence 50 in one run and $9.75bn at confidence 75 in another. A
20x spread, with the confidence moving the wrong way.

The suppression threshold added in session 1 does not fix that. It drops
low-confidence figures and passes high-confidence ones, and the 20x spread
lived on the high-confidence side.

So the question changes. Instead of "how big is this market", the model is
asked "which of these sources stated a figure, and what exactly did it say".
That is extraction, which is checkable: every claim must cite an evidence id,
and the quoted text must actually occur in that source. Claims that fail the
check are dropped rather than repaired.

When the sources disagree, the disagreement is the finding. Reporting a range
that spans 20x, and saying it does not converge, is more useful than picking
one end of it and attaching a confidence score.
"""

import logging
import re

from pydantic import BaseModel

from app.payload.rounding import round_sig

log = logging.getLogger("signal.sizing")

# Two figures within 2x of each other are the same claim told differently
# (different year, slightly different scope). Beyond that they are answers to
# different questions and averaging them would invent a third.
CONVERGENCE_RATIO = 2.0

_SCALES = {
    "trillion": 1e12, "tn": 1e12, "t": 1e12,
    "billion": 1e9, "bn": 1e9, "b": 1e9,
    "million": 1e6, "mn": 1e6, "m": 1e6,
    "thousand": 1e3, "k": 1e3,
}

_FIGURE = re.compile(
    r"(?:\$|usd|us\$|€|£)?\s*"
    r"(\d+(?:[.,]\d+)?)\s*"
    r"(trillion|billion|million|thousand|tn|bn|mn|[tbmk])\b",
    re.IGNORECASE,
)


def parse_usd(text: str) -> float | None:
    """Parse the first currency magnitude out of a quoted figure.

    Done here rather than asked of the model: the model has already shown it
    will produce a plausible number on request, and this is arithmetic, which
    is exactly the part that does not need a language model.
    """
    if not text:
        return None
    match = _FIGURE.search(text)
    if not match:
        return None
    try:
        amount = float(match.group(1).replace(",", ""))
    except ValueError:
        return None
    return amount * _SCALES[match.group(2).lower()]


def format_usd(value: float | None) -> str:
    """Format a *derived* amount at two significant figures.

    Only for numbers this module computes -- the ends of a range, a spread.
    `figure_text` is never passed through here: it is a quotation, and rounding
    a quotation to $500M when the source wrote $496.1m misquotes the source.
    """
    if value is None:
        return "—"
    for limit, suffix, scale in (
        (1e12, "T", 1e12), (1e9, "B", 1e9), (1e6, "M", 1e6), (1e3, "K", 1e3)
    ):
        if abs(value) >= limit:
            trimmed = round_sig(value / scale, 2)
            number = int(trimmed) if trimmed == int(trimmed) else trimmed
            return f"${number}{suffix}"
    return f"${round(value)}"


def _domain(url: str) -> str:
    match = re.search(r"https?://(?:www\.)?([^/]+)", url or "")
    return match.group(1) if match else ""


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


class SizingClaim(BaseModel):
    evidence_id: str
    source_name: str
    figure_text: str
    value_usd: float | None = None
    year: int | None = None
    scope: str = ""
    url: str = ""


class MarketSizing(BaseModel):
    claims: list[SizingClaim] = []
    low_usd: float | None = None
    high_usd: float | None = None
    converges: bool = False
    display: str = ""
    basis: str = ""


def _verify(claim: dict, by_id: dict) -> SizingClaim | None:
    """Accept a claim only if the source it cites really says it.

    Two ways a claim dies here: it cites an id that was never collected, or it
    quotes a figure that does not occur in the source it points at. Both mean
    the model wrote the number rather than found it, which is the failure this
    whole module exists to prevent.
    """
    evidence_id = str(claim.get("evidence_id") or "").strip()
    item = by_id.get(evidence_id)
    if not item:
        log.warning("sizing claim cites unknown evidence id %r", evidence_id)
        return None

    figure = str(claim.get("figure_text") or "").strip()
    if not figure:
        return None

    haystack = _normalise(f"{item.get('title', '')} {item.get('snippet', '')}")
    if _normalise(figure) not in haystack:
        log.warning(
            "sizing claim not found in its cited source | id=%s figure=%r",
            evidence_id, figure[:60],
        )
        return None

    year = claim.get("year")
    try:
        year = int(year) if year is not None else None
    except (TypeError, ValueError):
        year = None
    if year is not None and not (1990 <= year <= 2100):
        year = None

    return SizingClaim(
        evidence_id=evidence_id,
        source_name=item.get("display_name", "Unknown source"),
        figure_text=figure,
        value_usd=parse_usd(figure),
        year=year,
        scope=str(claim.get("scope") or "").strip(),
        url=item.get("url", ""),
    )


def build_market_sizing(raw, evidence: list[dict]) -> MarketSizing:
    by_id = {e.get("id"): e for e in evidence}
    claims = []

    # `.get("claims", [])` is not enough: the key can be present and null.
    raw_claims = (raw.get("claims") or []) if isinstance(raw, dict) else []

    for candidate in raw_claims:
        if isinstance(candidate, dict):
            verified = _verify(candidate, by_id)
            if verified:
                claims.append(verified)

    # Deduplicate on the figure itself: the same headline scraped twice is one
    # claim, and counting it twice would make disagreement look like agreement.
    seen, unique = set(), []
    for claim in claims:
        key = _normalise(claim.figure_text)
        if key not in seen:
            seen.add(key)
            unique.append(claim)
    claims = unique

    scanned = len(evidence)

    if not claims:
        return MarketSizing(
            claims=[],
            display="No sizing figures appeared in the collected sources.",
            basis=(
                f"{scanned} sources were scanned and none stated a market size. "
                f"No figure is estimated in place of one."
            ),
        )

    values = [c.value_usd for c in claims if c.value_usd]
    low = min(values) if values else None
    high = max(values) if values else None

    if len(claims) == 1:
        only = claims[0]
        where = _domain(only.url) or only.source_name
        return MarketSizing(
            claims=claims, low_usd=low, high_usd=high, converges=True,
            display=f"{only.figure_text} — {where}, the only source to state a figure.",
            basis=f"One of {scanned} collected sources stated a market size.",
        )

    if not low or not high:
        return MarketSizing(
            claims=claims, low_usd=low, high_usd=high, converges=False,
            display=f"{len(claims)} sources state figures, but none could be parsed "
                    f"into a comparable amount.",
            basis=f"{len(claims)} of {scanned} collected sources stated a figure.",
        )

    converges = (high / low) <= CONVERGENCE_RATIO

    if converges:
        display = (f"{len(claims)} sources imply {format_usd(low)}–{format_usd(high)}.")
    else:
        display = (
            f"{len(claims)} sources imply figures from {format_usd(low)} to "
            f"{format_usd(high)} — the estimates do not converge."
        )

    years = sorted({c.year for c in claims if c.year})
    scope_note = ""
    if len(years) > 1:
        scope_note = (f" Figures target different years ({', '.join(map(str, years))}), "
                      f"so they are not directly comparable.")

    # A spread this wide is almost never one market measured differently -- it
    # is different things being measured. Say so rather than presenting it as
    # disagreement about a single quantity.
    scopes = {c.scope.strip().lower() for c in claims if c.scope.strip()}
    if not converges and len(scopes) > 1:
        scope_note += (f" They also measure {len(scopes)} different scopes, so the "
                       f"spread is partly a difference in what is being counted.")

    return MarketSizing(
        claims=claims, low_usd=low, high_usd=high, converges=converges,
        display=display,
        basis=(f"{len(claims)} of {scanned} collected sources stated a figure, quoted "
               f"verbatim and attributed. Spread is {round(high / low, 1)}x."
               + scope_note),
    )
