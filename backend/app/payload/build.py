"""Assembles the `report` block.

Additive by construction: this reads the existing `intelligence`, `synthesis`,
`signals` and `evidence` and produces a parallel view of them. Nothing it
touches is removed, so the deployed frontend keeps rendering from the original
keys until session 2 moves it across.
"""

from app.payload.definitions import (
    DEPRECATED_FIELDS,
    LIST_METRIC_KEYS,
    SCORE_SCALE,
    metric_definitions,
    source_label,
)
from app.payload.envelopes import Estimate, band_for_confidence
from app.payload.sizing import build_market_sizing
from app.payload.normalise import (
    assign_evidence_ids,
    build_insight_list,
    build_signal_report,
    dedupe_headlines,
    evidence_summary,
    market_estimate,
    tidy_figures,
)

# Which section each ranked list lives in, in render order.
LIST_SOURCES = {
    "customer": ("customer_segments", "pain_points", "desired_outcomes",
                 "behavior_patterns", "opportunity_areas"),
    "market": ("key_trends", "emerging_trends", "market_drivers"),
    "competitive": ("competitors", "competitive_threats", "positioning_gaps",
                    "white_space_opportunities", "differentiation_opportunities"),
    "synthesis": ("why_now", "key_opportunities", "key_risks",
                  "potential_moats", "execution_ideas"),
}


def _score_estimate(value, basis: str, confidence: int | None = None) -> Estimate:
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        number = 0
    return Estimate(
        value=number,
        display=str(number),
        unit=None,
        confidence=confidence,
        confidence_band=band_for_confidence(confidence),
        basis=basis,
        source_count=0,
        evidence_ids=[],
        collected=True,
    )


def build_report(intelligence: dict, synthesis: dict, signals: dict,
                 evidence: list[dict], degraded_reason: str | None = None) -> dict:
    evidence = assign_evidence_ids(evidence)

    signal_report, unavailable = build_signal_report(signals, evidence)
    market = intelligence.get("market") or {}

    lists = {}
    for section, keys in LIST_SOURCES.items():
        container = synthesis if section == "synthesis" else (intelligence.get(section) or {})
        for key in keys:
            lists[key] = build_insight_list(
                key,
                container.get(key) or [],
                LIST_METRIC_KEYS.get(key, "score"),
                evidence,
            ).model_dump()

    sources: dict[str, int] = {}
    for item in evidence:
        sources[item["source_key"]] = sources.get(item["source_key"], 0) + 1

    # "Monitor" is what normalise_synthesis fills in when the model output was
    # unparseable -- it is the default, not a judgement. Measured across 15
    # variance runs, 2 came back with a completely empty briefing and were
    # served as a considered "Monitor" verdict with 30 sources listed beneath
    # it. v1 keeps the default so the deployed page still renders; v2 refuses
    # to state a verdict it does not have.
    recommendation = synthesis.get("build_recommendation") or {}
    empty_synthesis = not (synthesis.get("executive_summary") or "").strip()
    verdict_unavailable = bool(degraded_reason) or empty_synthesis

    return {
        "schema_version": 2,
        "verdict": {
            "decision": None if verdict_unavailable else recommendation.get("decision"),
            "decision_unavailable_reason": (
                (degraded_reason or "the model returned no synthesis for this topic")
                if verdict_unavailable else None
            ),
            "reason": "" if verdict_unavailable else recommendation.get("reason", ""),
            "executive_summary": tidy_figures(synthesis.get("executive_summary", "")),
            "top_reason_to_build": tidy_figures(synthesis.get("top_reason_to_build", "")),
            "biggest_risk": tidy_figures(synthesis.get("biggest_risk", "")),
            "market_pulse": _score_estimate(
                synthesis.get("market_pulse"),
                "The model's overall read of market conditions across every section it wrote.",
            ).model_dump(),
            "confidence": _score_estimate(
                synthesis.get("confidence"),
                synthesis.get("confidence_explanation")
                or "How well the collected evidence supported the conclusions.",
                confidence=synthesis.get("confidence"),
            ).model_dump(),
        },
        "headline": dedupe_headlines(synthesis),
        # Attributed claims. `market.market_size` below is the session-1
        # Estimate, kept only until session 3 switches the render across.
        "market_sizing": build_market_sizing(
            intelligence.get("market_sizing"), evidence
        ).model_dump(),
        "market": {
            "market_size": market_estimate(
                market.get("market_size"), "estimate", "market size", evidence
            ).model_dump(),
            "growth_rate": market_estimate(
                market.get("growth_rate"), "estimate", "growth rate", evidence
            ).model_dump(),
            "market_maturity": market_estimate(
                market.get("market_maturity"), "stage", "maturity read", evidence
            ).model_dump(),
            "future_outlook": market_estimate(
                market.get("future_outlook"), "direction", "outlook", evidence
            ).model_dump(),
        },
        "signals": signal_report,
        "signals_unavailable": unavailable,
        "lists": lists,
        # Filter keys with a human label attached, so no view has to map `ddgs`
        # onto "Web search" itself.
        "sources": [
            {"source_key": key, "display_name": source_label(key), "count": count}
            for key, count in sorted(sources.items(), key=lambda kv: -kv[1])
        ],
    }


def attach(result: dict) -> dict:
    """Add the v2 block and its top-level companions to a v1 response."""
    evidence = result.get("evidence") or []

    report = build_report(
        result.get("intelligence") or {},
        result.get("synthesis") or {},
        result.get("signals") or {},
        evidence,
        result.get("degraded_reason"),
    )

    result["report"] = report
    result["metric_definitions"] = [d.model_dump() for d in metric_definitions()]
    result["score_scale"] = SCORE_SCALE
    result["evidence_summary"] = evidence_summary(evidence)
    result["signals_unavailable"] = report["signals_unavailable"]
    result["deprecated_fields"] = DEPRECATED_FIELDS
    return result
