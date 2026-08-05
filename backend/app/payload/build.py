"""Assembles the `report` block.

Additive by construction: this reads the existing `intelligence`, `synthesis`,
`signals` and `evidence` and produces a parallel view of them. Nothing it
touches is removed, so the deployed frontend keeps rendering from the original
keys until session 2 moves it across.
"""

from app.payload.definitions import (
    REMOVED_FIELDS,
    LIST_METRIC_KEYS,
    SCORE_SCALE,
    metric_definitions,
    source_label,
)
from app.payload.envelopes import Estimate, band_for_confidence
import logging

from app.payload.sizing import build_market_growth, build_market_sizing
from app.payload.normalise import (
    MIN_REPORTABLE_CONFIDENCE,
    assign_evidence_ids,
    build_insight_list,
    build_signal_report,
    dedupe_headlines,
    evidence_summary,
    figure_conflicts,
    market_estimate,
    supersede,
    tidy_figures,
)

# Below this many ranked sources, a verdict is a guess dressed as a finding.
# Chosen against the observed failure: "Cold Plunge Tubs" collected a handful
# of items and still produced a full briefing with an execution plan.
MIN_EVIDENCE_FOR_VERDICT = 8

log = logging.getLogger("signal.payload")

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

    sizing = build_market_sizing(intelligence.get("market_sizing"), evidence)
    growth = build_market_growth(intelligence.get("market_sizing"), evidence)

    # Structural, not prose. A frontend was rendering "No reliable briefing for
    # X" above a full briefing -- Why Now, moats, an execution plan -- because
    # nothing in the payload let it gate the body on the same judgement it used
    # for the headline. A flag can be gated on; a sentence cannot.
    confidence = synthesis.get("confidence") or 0
    reasons = []
    if len(evidence) < MIN_EVIDENCE_FOR_VERDICT:
        reasons.append(
            f"only {len(evidence)} sources were collected, below the "
            f"{MIN_EVIDENCE_FOR_VERDICT} needed for a verdict"
        )
    if confidence and confidence < MIN_REPORTABLE_CONFIDENCE:
        reasons.append(
            f"the model rated its own confidence at {confidence}/100, below the "
            f"{MIN_REPORTABLE_CONFIDENCE} reporting threshold"
        )

    # A section built entirely from the lowest band is inference, not evidence.
    inferred_only = sorted(
        key for key, container in lists.items()
        if container["items"] and all(i["score"] == 50 for i in container["items"])
    )

    evidence_sufficient = not reasons and not verdict_unavailable

    return {
        "schema_version": 2,
        "evidence_sufficient": evidence_sufficient,
        "insufficient_reason": "; ".join(reasons) or None,
        # Lists a client should treat as suggestive rather than supported.
        "inferred_only_sections": inferred_only,
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
            # market_pulse is gone. It drove a large number above the verdict,
            # had no entry in metric_definitions, and its only description was
            # circular -- "the model's overall read" says nothing about how it
            # is computed, because nothing computes it. Variance testing
            # measured it spreading 92 points across five identical runs
            # (8, 100, 100, 94, 100), so it was also the least stable number in
            # the payload. A composite nobody can define and nobody can
            # reproduce is not a summary; the verdict and its confidence carry
            # that job.
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
        "market_sizing": sizing.model_dump(),
        "market_growth": growth.model_dump(),
        "market": {
            # Suppressed whenever the sources stated a figure themselves. An
            # extracted, quoted, attributed number and a generated one are not
            # two opinions to weigh -- one is checkable and the other is not.
            "market_size": supersede(
                market_estimate(
                    market.get("market_size"), "estimate", "market size", evidence,
                    field="market_size",
                ).model_dump(),
                len(sizing.claims), "market size",
            ),
            "growth_rate": supersede(
                market_estimate(
                    market.get("growth_rate"), "estimate", "growth rate", evidence,
                    field="growth_rate",
                ).model_dump(),
                len(growth.claims), "growth rate",
            ),
            # Labels are interpolated into prose ("none stated a {label}"), so
            # they read as noun phrases that take "a", not as field names.
            "market_maturity": market_estimate(
                market.get("market_maturity"), "stage", "maturity stage", evidence,
                field="market_maturity",
            ).model_dump(),
            "future_outlook": market_estimate(
                market.get("future_outlook"), "direction", "forward outlook", evidence,
                field="future_outlook",
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

    # Fail loudly rather than shipping two numbers for one quantity. This is
    # the guard against the precedence rule being reintroduced in a panel
    # nobody thought to check.
    conflicts = figure_conflicts(report)
    if conflicts:
        log.warning("conflicting figures in one response | %s", "; ".join(conflicts))

    summary = evidence_summary(evidence)

    result["report"] = report
    result["metric_definitions"] = [d.model_dump() for d in metric_definitions()]
    result["score_scale"] = SCORE_SCALE
    result["evidence_summary"] = summary
    result["signals_unavailable"] = report["signals_unavailable"]
    result["removed_fields"] = REMOVED_FIELDS
    result["figure_conflicts"] = conflicts

    # One sentence the frontend renders verbatim. Kept here rather than in the
    # frontend so the wording is the same on every surface and can be changed
    # in one place -- and so the disclosure ships with the data it describes
    # rather than depending on a client remembering to add it.
    collected_at = (result.get("meta") or {}).get("generated_at", "")
    when = collected_at.split("T")[0] if collected_at else "today"
    result["run_disclosure"] = (
        f"One reading of {summary['used']} sources collected {when}. "
        f"Re-running may surface different findings."
    )
    return result
