"""AI stage.

PORTFOLIO_MODE picks the path:

  True   one merged call  -> app.intelligence.unified_intelligence
  False  the original four sequential calls -> app.intelligence.intelligence_engine
         plus app.synthesis.gemini_synthesis

Caching moved out to AnalysisService. It used to live here, which meant a
cache hit was only consulted after collection had already run.
"""

import time
from datetime import datetime

from app import config
from app.intelligence.unified_intelligence import build_everything
from app.services.json_utils import normalise_synthesis


def _legacy(topic, evidence, signals, known_competitors):
    """The original pipeline: three extraction calls, then synthesis."""
    from app.intelligence.intelligence_engine import build_intelligence
    from app.synthesis.gemini_synthesis import generate_synthesis

    started = time.time()
    intelligence = build_intelligence(
        topic=topic,
        evidence=evidence,
        signals=signals,
        known_competitors=known_competitors,
    )
    intelligence_time = round(time.time() - started, 2)
    print(f"AI Analysis (intelligence, 3 calls): {intelligence_time}s")

    started = time.time()
    synthesis = normalise_synthesis(
        generate_synthesis(topic=topic, intelligence=intelligence, signals=signals)
    )
    synthesis_time = round(time.time() - started, 2)
    print(f"AI Analysis (synthesis, 1 call): {synthesis_time}s")

    return intelligence, synthesis, intelligence_time, synthesis_time


def _unified(topic, evidence, signals, known_competitors):
    """One call for all four sections."""
    started = time.time()
    bundle, ok = build_everything(
        topic=topic,
        evidence=evidence,
        signals=signals,
        known_competitors=known_competitors,
    )
    ai_time = round(time.time() - started, 2)

    print(f"AI Analysis: {ai_time}s (1 call, {'ok' if ok else 'DEGRADED'})")

    intelligence = {
        "customer": bundle["customer"],
        "market": bundle["market"],
        "competitive": bundle["competitive"],
    }

    # There is no separable synthesis stage any more -- the model emits it in
    # the same response. `intelligence_time` carries the call, and
    # `synthesis_time` the parse and contract-normalisation that extracts it,
    # so both fields stay real rather than being invented.
    return intelligence, bundle["synthesis"], ai_time, 0.0


def public_evidence(evidence):
    """The ranked evidence, in a shape that is safe and stable to publish.

    Collectors return heterogeneous dicts -- YouTube carries view counts,
    Product Hunt carries vote rates, Google Trends carries none of the above.
    Publishing those verbatim would make the response shape depend on which
    collectors happened to be enabled, so this projects every source onto one
    fixed set of keys instead.

    `used_in_prompt` is the honest part: only the first N ranked items are
    serialised into the prompt, so only those actually informed the analysis.
    The rest were collected and outranked, and saying so is more useful than
    implying all 30 were read.
    """
    cutoff = config.prompt_evidence_items()
    out = []

    for rank, item in enumerate(evidence, 1):
        snippet = " ".join((item.get("snippet") or "").split())
        out.append({
            "rank": rank,
            "source": item.get("source", "unknown"),
            "title": (item.get("title") or "").strip(),
            "url": item.get("url", "") or "",
            "snippet": snippet[:config.EVIDENCE_SNIPPET_CHARS],
            # Empty for collectors that are not query-driven.
            "query": item.get("query", "") or "",
            "used_in_prompt": rank <= cutoff,
        })

    return out


def analyze_topic(
    topic,
    evidence,
    signals,
    known_competitors=None,
    collection_time=0.0,
):
    known_competitors = known_competitors or []

    ai_start = time.time()

    if config.PORTFOLIO_MODE:
        intelligence, synthesis, intelligence_time, synthesis_time = _unified(
            topic, evidence, signals, known_competitors
        )
    else:
        intelligence, synthesis, intelligence_time, synthesis_time = _legacy(
            topic, evidence, signals, known_competitors
        )

    ai_time = round(time.time() - ai_start, 2)
    parse_time = round(max(0.0, ai_time - intelligence_time - synthesis_time), 2)

    if config.PORTFOLIO_MODE:
        synthesis_time = parse_time

    print(f"JSON Parsing: {parse_time}s")

    return {
        "meta": {
            "topic": topic,
            "cached": False,
            "generated_at": datetime.utcnow().isoformat(),
            "intelligence_time": intelligence_time,
            "synthesis_time": synthesis_time,
            # Additive fields. Existing frontend keys above are untouched.
            "collection_time": collection_time,
            "ai_time": ai_time,
            "parse_time": parse_time,
            "evidence_count": len(evidence),
            # How many of those reached the prompt. The frontend needs this to
            # explain `used_in_prompt` without hardcoding a backend constant.
            "evidence_used": min(len(evidence), config.prompt_evidence_items()),
            "portfolio_mode": config.PORTFOLIO_MODE,
            "total_time": round(collection_time + ai_time, 2),
        },
        "signals": signals,
        "intelligence": intelligence,
        "synthesis": synthesis,
        # Additive. Always present, empty when disabled, so the frontend never
        # has to branch on the key existing.
        "evidence": public_evidence(evidence) if config.INCLUDE_EVIDENCE else [],
    }
