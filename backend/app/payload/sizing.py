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
from typing import Literal

from pydantic import BaseModel

from app.payload.rounding import round_sig

log = logging.getLogger("signal.sizing")

# Two figures within 2x of each other are the same claim told differently
# (different year, slightly different scope). Beyond that they are answers to
# different questions and averaging them would invent a third.
CONVERGENCE_RATIO = 2.0

# Growth rates converge on percentage points, not on a ratio. 4% and 8% are
# 2x apart but only four points, which a reader reads as broad agreement;
# 40% and 80% are the same ratio and a completely different disagreement.
GROWTH_CONVERGENCE_POINTS = 5.0

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


# How well a claim's scope matches the topic that was asked about.
#
# Two sources both sizing "the global SaaS market" are honest claims and
# useless as a headline for "B2B SaaS for HR" -- they describe a category
# several orders of magnitude wider. Printing the scope was not enough: the
# figures still drove the hero range.
ScopeMatch = Literal["exact", "broader", "unclear"]

_SCOPE_VALUES = ("exact", "broader", "unclear")


class SizingClaim(BaseModel):
    evidence_id: str
    source_name: str
    figure_text: str
    value_usd: float | None = None
    year: int | None = None
    scope: str = ""
    scope_match: ScopeMatch = "unclear"
    url: str = ""


class GrowthClaim(BaseModel):
    evidence_id: str
    source_name: str
    figure_text: str
    value_pct: float | None = None
    period: str = ""
    scope: str = ""
    scope_match: ScopeMatch = "unclear"
    url: str = ""


class MarketSizing(BaseModel):
    claims: list[SizingClaim] = []
    low_usd: float | None = None
    high_usd: float | None = None
    converges: bool = False
    # Which scope band the headline range was computed from, so a reader can
    # see that a range of "broader" figures is not a range for their topic.
    range_scope: ScopeMatch | None = None
    display: str = ""
    basis: str = ""


class MarketGrowth(BaseModel):
    claims: list[GrowthClaim] = []
    low_pct: float | None = None
    high_pct: float | None = None
    converges: bool = False
    range_scope: ScopeMatch | None = None
    display: str = ""
    basis: str = ""


_PERCENT_FIGURE = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")


def parse_pct(text: str) -> float | None:
    """First percentage in a quoted figure. `13.7% CAGR` -> 13.7."""
    match = _PERCENT_FIGURE.search(text or "")
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


def _scope_match(raw) -> str:
    value = str(raw or "").strip().lower()
    return value if value in _SCOPE_VALUES else "unclear"


def _cited_source(claim: dict, by_id: dict, kind: str):
    """The evidence item a claim cites, if the source really says it.

    Two ways a claim dies here: it cites an id that was never collected, or it
    quotes a figure that does not occur in the source it points at. Both mean
    the model wrote the number rather than found it, which is the failure this
    whole module exists to prevent.
    """
    evidence_id = str(claim.get("evidence_id") or "").strip()
    item = by_id.get(evidence_id)
    if not item:
        log.warning("%s claim cites unknown evidence id %r", kind, evidence_id)
        return None, "", ""

    figure = str(claim.get("figure_text") or "").strip()
    if not figure:
        return None, "", ""

    haystack = _normalise(f"{item.get('title', '')} {item.get('snippet', '')}")
    if _normalise(figure) not in haystack:
        log.warning(
            "%s claim not found in its cited source | id=%s figure=%r",
            kind, evidence_id, figure[:60],
        )
        return None, "", ""

    return item, evidence_id, figure


def _verify(claim: dict, by_id: dict) -> SizingClaim | None:
    item, evidence_id, figure = _cited_source(claim, by_id, "sizing")
    if item is None:
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
        scope_match=_scope_match(claim.get("scope_match")),
        url=item.get("url", ""),
    )


def _verify_growth(claim: dict, by_id: dict) -> GrowthClaim | None:
    item, evidence_id, figure = _cited_source(claim, by_id, "growth")
    if item is None:
        return None

    return GrowthClaim(
        evidence_id=evidence_id,
        source_name=item.get("display_name", "Unknown source"),
        figure_text=figure,
        value_pct=parse_pct(figure),
        period=str(claim.get("period") or "").strip(),
        scope=str(claim.get("scope") or "").strip(),
        scope_match=_scope_match(claim.get("scope_match")),
        url=item.get("url", ""),
    )


def _pick_scope_band(claims):
    """The claims a headline range may be computed from.

    Exact-scope claims win outright. Falling back to broader ones is allowed --
    they are still real, attributed figures and worth showing -- but the two
    are never mixed, because a range whose ends measure different categories
    is not a range of anything.
    """
    for band in ("exact", "broader", "unclear"):
        subset = [c for c in claims if c.scope_match == band]
        if subset:
            return band, subset
    return None, []


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

    # Every verified claim is still published. Only the *range* is restricted
    # to one scope band, so a reader sees all the evidence but the headline
    # figure describes one thing.
    band, in_band = _pick_scope_band(claims)
    widest = ""
    if band == "broader":
        subject = (in_band[0].scope or "a wider category").strip()
        widest = (f" These figures describe {subject}, which is broader than the "
                  f"topic asked about.")
    elif band == "unclear":
        widest = (" It is not clear from the sources whether these figures "
                  "describe this topic or a wider category.")

    # Claims held back from the range because they measure something else.
    # Stated wherever a basis is produced, not only on the multi-claim path --
    # a lone in-scope figure sitting beside two out-of-scope ones is exactly
    # the case a reader needs told.
    excluded = len(claims) - len(in_band)
    excluded_note = (
        f" {excluded} further claim(s) were collected at a different scope and "
        f"are excluded from this range." if excluded else ""
    )

    values = [c.value_usd for c in in_band if c.value_usd]
    low = min(values) if values else None
    high = max(values) if values else None

    if len(in_band) == 1:
        only = in_band[0]
        where = _domain(only.url) or only.source_name
        return MarketSizing(
            claims=claims, low_usd=low, high_usd=high, converges=True,
            range_scope=band,
            display=f"{only.figure_text} — {where}, the only source to state a figure."
                    + widest,
            basis=(f"One of {scanned} collected sources stated a market size at "
                   f"this scope." + excluded_note),
        )

    if not low or not high:
        return MarketSizing(
            claims=claims, low_usd=low, high_usd=high, converges=False,
            range_scope=band,
            display=f"{len(in_band)} sources state figures, but none could be parsed "
                    f"into a comparable amount.",
            basis=(f"{len(claims)} of {scanned} collected sources stated a figure."
                   + excluded_note),
        )

    converges = (high / low) <= CONVERGENCE_RATIO

    if converges:
        display = f"{len(in_band)} sources imply {format_usd(low)}–{format_usd(high)}."
    else:
        display = (
            f"{len(in_band)} sources imply figures from {format_usd(low)} to "
            f"{format_usd(high)} — the estimates do not converge."
        )
    display += widest

    years = sorted({c.year for c in in_band if c.year})
    scope_note = ""
    if len(years) > 1:
        scope_note = (f" Figures target different years ({', '.join(map(str, years))}), "
                      f"so they are not directly comparable.")

    # A spread this wide is almost never one market measured differently -- it
    # is different things being measured. Say so rather than presenting it as
    # disagreement about a single quantity.
    scopes = {c.scope.strip().lower() for c in in_band if c.scope.strip()}
    if not converges and len(scopes) > 1:
        scope_note += (f" They also measure {len(scopes)} different scopes, so the "
                       f"spread is partly a difference in what is being counted.")

    scope_note += excluded_note

    return MarketSizing(
        claims=claims, low_usd=low, high_usd=high, converges=converges,
        range_scope=band,
        display=display,
        basis=(f"{len(in_band)} of {scanned} collected sources stated a figure at "
               f"this scope, quoted verbatim and attributed. "
               f"Spread is {round(high / low, 1)}x."
               + scope_note),
    )


def build_market_growth(raw, evidence: list[dict]) -> MarketGrowth:
    """Growth rates, extracted and attributed the same way sizing is.

    Exists because the model's own `growth_rate` estimate was landing on
    figures no source had stated -- "14% CAGR" against sources saying 13.7%
    and 10.60%. An extracted figure can be checked; a generated one cannot.
    """
    by_id = {e.get("id"): e for e in evidence}
    raw_claims = (raw.get("growth_claims") or []) if isinstance(raw, dict) else []

    claims = []
    for candidate in raw_claims:
        if isinstance(candidate, dict):
            verified = _verify_growth(candidate, by_id)
            if verified:
                claims.append(verified)

    seen, unique = set(), []
    for claim in claims:
        key = _normalise(claim.figure_text)
        if key not in seen:
            seen.add(key)
            unique.append(claim)
    claims = unique

    scanned = len(evidence)

    if not claims:
        return MarketGrowth(
            claims=[],
            display="No growth figure appeared in the collected sources.",
            basis=(f"{scanned} sources were scanned and none stated a growth rate "
                   f"or CAGR."),
        )

    band, in_band = _pick_scope_band(claims)
    widest = ""
    if band == "broader":
        subject = (in_band[0].scope or "a wider category").strip()
        widest = (f" These rates describe {subject}, which is broader than the "
                  f"topic asked about.")

    values = [c.value_pct for c in in_band if c.value_pct is not None]
    low = min(values) if values else None
    high = max(values) if values else None

    def pct(value):
        return f"{value:g}%"

    if len(in_band) == 1:
        only = in_band[0]
        where = _domain(only.url) or only.source_name
        return MarketGrowth(
            claims=claims, low_pct=low, high_pct=high, converges=True,
            range_scope=band,
            display=f"{only.figure_text} — {where}, the only source to state a rate."
                    + widest,
            basis=f"One of {scanned} collected sources stated a growth rate.",
        )

    if low is None or high is None:
        return MarketGrowth(
            claims=claims, converges=False, range_scope=band,
            display=f"{len(in_band)} sources state growth rates, but none could be "
                    f"parsed into a comparable figure.",
            basis=f"{len(claims)} of {scanned} collected sources stated a rate.",
        )

    # Growth rates are already a ratio, so a ratio-of-ratios is the wrong test.
    # Percentage points is what a reader compares.
    converges = (high - low) <= GROWTH_CONVERGENCE_POINTS
    display = (f"{len(in_band)} sources imply {pct(low)}–{pct(high)}."
               if converges else
               f"{len(in_band)} sources imply rates from {pct(low)} to {pct(high)} "
               f"— they do not converge.") + widest

    return MarketGrowth(
        claims=claims, low_pct=low, high_pct=high, converges=converges,
        range_scope=band,
        display=display,
        basis=(f"{len(in_band)} of {scanned} collected sources stated a growth rate "
               f"at this scope, quoted verbatim and attributed."),
    )
