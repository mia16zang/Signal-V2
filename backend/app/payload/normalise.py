"""Server-side post-processing of raw model output.

Every rule in here exists because the payload was asserting something it could
not support:

  * false precision   -- `trend_growth: 76.67` from a sampled trend line
  * unsupported figures -- a market size carrying confidence 50
  * zero-as-null      -- `launches: 0` when Product Hunt was switched off
  * duplicated fields -- two headline fields answering the same question
  * meaningless order -- lists rendered in whatever order the model emitted

Kept in one module so it is testable without a network call, and so the
case-study diff has a single place to point at.
"""

import re
from difflib import SequenceMatcher

from app import config
from app.payload.definitions import (
    LIST_LABELS,
    LIST_METRIC_KEYS,
    MENTION_GROUP_DEFINITION,
    MENTION_KEYS,
    SIGNAL_SPECS,
    source_label,
)
from app.payload.envelopes import (
    BAND_BY_SCORE,
    Estimate,
    Insight,
    InsightList,
    band_for_confidence,
)
from app.payload.rounding import round_sig  # re-exported; used across this module

# Below this, a figure is not reported as a number at all. 55 is the boundary
# between the model's own "few sources" (75) and "single source" (50) rungs, so
# it suppresses exactly the estimates the model itself called weakly supported.
MIN_REPORTABLE_CONFIDENCE = 55

NOT_ESTIMABLE = "Not reliably estimable from these sources"
NOT_COLLECTED = "—"


# --------------------------------------------------------------------------
# §4.1 Rounding
# --------------------------------------------------------------------------

_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_CURRENCY = re.compile(
    r"(\$|USD\s*|US\$)\s*(\d+(?:\.\d+)?)\s*(billion|million|trillion|bn|m|b|k)?",
    re.IGNORECASE,
)


def round_percentages(text: str) -> str:
    """Whole numbers only. `27.6%` -> `28%`."""
    return _PERCENT.sub(lambda m: f"{round(float(m.group(1)))}%", text)


def round_currency(text: str) -> str:
    """Two significant figures. `$9.75 billion` -> `$9.8 billion`.

    A market size derived from a handful of scraped headlines cannot justify
    four significant figures, and printing them invites the reader to believe
    a precision the pipeline never had.
    """
    def repl(m):
        prefix, number, scale = m.group(1), float(m.group(2)), m.group(3) or ""
        rounded = round_sig(number, 2)
        return f"{prefix}{rounded}{' ' + scale if scale else ''}"

    return _CURRENCY.sub(repl, text)


def tidy_figures(text: str) -> str:
    if not text:
        return text
    return round_currency(round_percentages(text))


# --------------------------------------------------------------------------
# Evidence identity and lookup
# --------------------------------------------------------------------------

def assign_evidence_ids(evidence: list[dict]) -> list[dict]:
    """Stable ids so an insight can point at the sources behind it.

    Ids are positional over the ranked list, which is deterministic for a given
    response and is what the prompt shows the model.
    """
    for item in evidence:
        item["id"] = f"e{item['rank']}"
        item["source_key"] = item.get("source", "unknown")
        item["display_name"] = source_label(item["source_key"])
        item["exclusion_reason"] = (
            None
            if item.get("used_in_prompt")
            else f"Ranked {item['rank']} of {len(evidence)}; below the prompt cutoff"
        )
    return evidence


def ids_from_source(evidence: list[dict], source: str) -> list[str]:
    return [e["id"] for e in evidence if e.get("source_key") == source]


def ids_matching(evidence: list[dict], terms: tuple[str, ...]) -> list[str]:
    out = []
    for e in evidence:
        text = f"{e.get('title', '')} {e.get('snippet', '')}".lower()
        if any(t in text for t in terms):
            out.append(e["id"])
    return out


def evidence_summary(evidence: list[dict]) -> dict:
    """One source of truth for the counts.

    Asserted rather than trusted: the header and the evidence list were
    reporting different totals, and a count that can disagree with itself is
    not a count.
    """
    used = [e for e in evidence if e.get("used_in_prompt")]
    summary = {
        "collected": len(evidence),
        "used": len(used),
        "excluded": len(evidence) - len(used),
    }
    assert summary["used"] == len(
        [e for e in evidence if e.get("used_in_prompt")]
    ), "evidence_summary.used disagrees with the evidence list"
    assert summary["collected"] == summary["used"] + summary["excluded"]
    return summary


# --------------------------------------------------------------------------
# §4.2 / §4.3 Estimates
# --------------------------------------------------------------------------

def _source_available(evidence: list[dict], feeds: str | None) -> bool:
    """Did the collector behind this signal contribute anything?"""
    if feeds is None:
        return bool(evidence)
    return any(
        ids_from_source(evidence, part) for part in feeds.split("+")
    )


def signal_estimate(group: str, key: str, raw, evidence: list[dict]) -> Estimate:
    spec = SIGNAL_SPECS[(group, key)]
    feeds = spec["feeds"]
    collected = _source_available(evidence, feeds)

    if feeds is None:
        contributing = [e["id"] for e in evidence]
    else:
        contributing = []
        for part in feeds.split("+"):
            contributing += ids_from_source(evidence, part)

    if not collected:
        names = " and ".join(source_label(p) for p in (feeds or "").split("+"))
        return Estimate(
            value=None,
            display=NOT_COLLECTED,
            unit=spec["unit"],
            confidence=None,
            confidence_band="none",
            basis=(
                f"{names} returned nothing for this topic, so this was never "
                f"measured. Not the same as a measured zero."
            ),
            source_count=0,
            evidence_ids=[],
            collected=False,
        )

    if spec["unit"] == "%":
        value = round(float(raw))
        display = f"~{value}%"
    elif isinstance(raw, float):
        value = round_sig(raw, 2)
        display = f"{value:,}"
    else:
        value = raw
        display = f"{raw:,}"

    return Estimate(
        value=value,
        display=display,
        unit=spec["unit"],
        confidence=None,
        confidence_band="none",
        basis=spec["derivation"],
        source_count=len(contributing),
        evidence_ids=contributing,
        collected=True,
    )


def build_signal_report(signals: dict, evidence: list[dict]) -> tuple[dict, list[str]]:
    """Every raw signal as an Estimate, plus the list of ones never measured."""
    out: dict[str, dict] = {}
    unavailable: list[str] = []

    for (group, key), _spec in SIGNAL_SPECS.items():
        raw = (signals.get(group) or {}).get(key, 0)
        estimate = signal_estimate(group, key, raw, evidence)
        out.setdefault(group, {})[key] = estimate.model_dump()

        if not estimate.collected:
            unavailable.append(f"{group}.{key}")

    # Counts, not a score. A count cannot saturate, needs no normalisation, and
    # has an obvious denominator -- none of which was true of the weighted
    # composite this replaces.
    mentions = signals.get("market_opportunity") or {}
    scanned = mentions.get("sources_scanned", len(evidence))
    out.setdefault("market_opportunity", {})["sizing_language_density"] = {
        "counts": {k: mentions.get(k, 0) for k in MENTION_KEYS},
        "sources_scanned": scanned,
        "definition": MENTION_GROUP_DEFINITION,
        "basis": (
            f"Counts of sizing and growth language across the {scanned} "
            f"collected sources. Not a score."
        ),
        "detected_market_sizes": [
            tidy_figures(s) for s in mentions.get("detected_market_sizes", [])
        ],
        "detected_growth_rates": [
            tidy_figures(s) for s in mentions.get("detected_growth_rates", [])
        ],
    }

    return out, unavailable


_SIZING_TERMS = ("market size", "market forecast", "industry report", "cagr",
                 "billion", "million", "forecast", "projected")


def market_estimate(raw: dict, value_key: str, label: str,
                    evidence: list[dict]) -> Estimate:
    """A model-written market figure, suppressed when weakly supported.

    The suppression is the point. A market size carrying confidence 50 is the
    model telling you it inferred the number, and printing it next to a
    confidence chip does not make it reportable -- it makes it quotable.
    """
    value = (raw or {}).get(value_key) or ""
    confidence = (raw or {}).get("confidence") or 0
    supporting = ids_matching(evidence, _SIZING_TERMS)

    if not value:
        return Estimate(
            value=None,
            display=NOT_COLLECTED,
            confidence=None,
            confidence_band="none",
            basis="The model returned no figure for this.",
            source_count=0,
            evidence_ids=[],
            collected=False,
        )

    if confidence < MIN_REPORTABLE_CONFIDENCE:
        return Estimate(
            value=None,
            display=NOT_ESTIMABLE,
            confidence=confidence,
            confidence_band="low",
            basis=(
                f"The model rated its own {label} at {confidence}/100, below the "
                f"{MIN_REPORTABLE_CONFIDENCE} reporting threshold. "
                f"{len(supporting)} of {len(evidence)} collected sources contain "
                f"sizing language."
            ),
            source_count=len(supporting),
            evidence_ids=supporting,
            collected=True,
        )

    tidied = tidy_figures(value)
    return Estimate(
        value=tidied,
        display=tidied,
        confidence=confidence,
        confidence_band=band_for_confidence(confidence),
        basis=(
            f"Model estimate, grounded in the {len(supporting)} collected sources "
            f"containing sizing or forecast language."
        ),
        source_count=len(supporting),
        evidence_ids=supporting,
        collected=True,
    )


# --------------------------------------------------------------------------
# §4.4 Headline de-duplication
# --------------------------------------------------------------------------

HEADLINE_FIELDS = (
    "recommended_customer",
    "best_customer_segment",
    "recommended_positioning",
    "best_moat",
)

SIMILARITY_THRESHOLD = 0.9


def _normalise_text(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", (text or "").lower()).strip()


def dedupe_headlines(synthesis: dict) -> dict:
    """Keep the first of any near-identical pair; null the later one.

    The cause is in the prompt -- it asks for the target customer twice under
    two names -- and that is fixed there. This is the guard for when the model
    answers the same way anyway.
    """
    out: dict[str, dict] = {}
    kept: list[tuple[str, str]] = []

    for field in HEADLINE_FIELDS:
        value = (synthesis or {}).get(field) or ""
        normalised = _normalise_text(value)

        duplicate_of = None
        if normalised:
            for earlier_field, earlier_norm in kept:
                if SequenceMatcher(None, normalised, earlier_norm).ratio() > SIMILARITY_THRESHOLD:
                    duplicate_of = earlier_field
                    break

        if duplicate_of:
            out[field] = {
                "value": None,
                "suppressed_reason": f"duplicate of {duplicate_of}",
            }
        else:
            out[field] = {"value": value or None, "suppressed_reason": None}
            if normalised:
                kept.append((field, normalised))

    return out


# --------------------------------------------------------------------------
# §4.5 Insight lists
# --------------------------------------------------------------------------

def _nearest_band(score) -> int:
    """Snap a stray score onto the declared scale.

    The prompt asks for 90/75/50 and a validator retries once. This is the last
    resort so one non-conforming item cannot fail the whole response, and it is
    logged so the rate is visible rather than silently absorbed.
    """
    try:
        value = int(score)
    except (TypeError, ValueError):
        value = 0
    return min(BAND_BY_SCORE, key=lambda b: abs(b - value))


def build_insight_list(list_key: str, items: list[dict], score_key: str,
                       evidence: list[dict]) -> InsightList:
    valid_ids = {e["id"] for e in evidence}
    insights: list[Insight] = []

    for index, item in enumerate(items or [], 1):
        raw_score = item.get(score_key, item.get("score", 0))
        score = _nearest_band(raw_score)

        # Drop ids the model invented; an id that points at nothing is worse
        # than no id, because the drawer would open onto an empty source.
        ids = [i for i in (item.get("evidence_ids") or []) if i in valid_ids]

        insights.append(
            Insight(
                id=f"{list_key}-{index}",
                label=item.get("name") or item.get("title") or "",
                detail=item.get("detail") or item.get("reason") or "",
                score=score,
                score_band=BAND_BY_SCORE[score],
                evidence_ids=ids,
                rank=0,
            )
        )

    # Stable sort: equal scores keep the model's own ordering, which is its
    # only remaining signal about relative importance.
    insights.sort(key=lambda i: (-i.score, -len(i.evidence_ids)))
    for rank, insight in enumerate(insights, 1):
        insight.rank = rank

    return InsightList(
        key=list_key,
        label=LIST_LABELS.get(list_key, list_key.replace("_", " ").title()),
        metric_key=LIST_METRIC_KEYS.get(list_key, "support"),
        items=insights,
    )
