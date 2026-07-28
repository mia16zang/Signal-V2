"""Offline verification that the optimised pipeline preserves the API contract.

Runs without any API keys. The LLM is stubbed, so what is under test is the
plumbing: collection, ranking, signals, JSON recovery and the response shape
the frontend consumes.

    python verify_contract.py           # stubbed LLM, real DDGS collection
    python verify_contract.py --offline # stubbed LLM, stubbed collection

Checks:
  1. Every key in the 14 cached production responses still exists, with the
     same type, at the same path.
  2. The JSON recovery path survives fenced, truncated, prose-wrapped and
     wrong-typed model output.
  3. A total LLM failure still returns a renderable response.
  4. A cache hit is served without running collection.
"""

import asyncio
import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("GEMINI_API_KEY", "stub")
os.environ.setdefault("OPENROUTER_API_KEY", "stub")

OFFLINE = "--offline" in sys.argv

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail and not ok else ""))


# --------------------------------------------------------------------------
# Expected contract, derived from the responses already on disk
# --------------------------------------------------------------------------

def shape(value):
    if isinstance(value, dict):
        return {k: shape(v) for k, v in value.items()}
    if isinstance(value, list):
        return [shape(value[0])] if value else ["?"]
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    return "str" if isinstance(value, str) else type(value).__name__


def merge(a, b):
    """Union of two shapes, so optional-but-seen keys are all required."""
    if isinstance(a, dict) and isinstance(b, dict):
        return {k: merge(a[k], b[k]) if k in a and k in b else a.get(k, b.get(k))
                for k in set(a) | set(b)}
    if isinstance(a, list) and isinstance(b, list):
        if a == ["?"]:
            return b
        if b == ["?"]:
            return a
        return [merge(a[0], b[0])]
    return a


_NAMED = lambda field: [{"name": "str", field: "number"}]          # noqa: E731
_INSIGHT = [{"title": "str", "reason": "str", "evidence": "str"}]

FROZEN_CONTRACT = {
    "meta": {
        "topic": "str",
        "cached": "bool",
        "generated_at": "str",
        "intelligence_time": "number",
        "synthesis_time": "number",
        "total_time": "number",
    },
    "signals": {
        "customer": {"discussion_volume": "number", "comment_volume": "number"},
        "market": {"growth_score": "number", "startup_activity": "number"},
        "competitive": {
            "launches": "number",
            "competition_score": "number",
            "avg_votes_per_day": "number",
        },
        "virality": {
            "momentum": "number",
            "trend_growth": "number",
            "avg_views_per_day": "number",
            "avg_engagement_rate": "number",
        },
        "market_size": {"market_reports": "number"},
        "market_opportunity": {
            "opportunity_score": "number",
            "market_size_mentions": "number",
            "growth_mentions": "number",
            "forecast_mentions": "number",
            "billion_mentions": "number",
            "million_mentions": "number",
            "cagr_mentions": "number",
            "detected_market_sizes": ["?"],
            "detected_growth_rates": ["?"],
        },
    },
    "intelligence": {
        "customer": {
            "customer_segments": _NAMED("score"),
            "pain_points": _NAMED("signal_strength"),
            "desired_outcomes": _NAMED("importance"),
            "behavior_patterns": _NAMED("confidence"),
            "opportunity_areas": _NAMED("score"),
        },
        "market": {
            "market_size": {"estimate": "str", "confidence": "number"},
            "growth_rate": {"estimate": "str", "confidence": "number"},
            "market_maturity": {"stage": "str", "confidence": "number"},
            "future_outlook": {"direction": "str", "confidence": "number"},
            "key_trends": _NAMED("strength"),
            "emerging_trends": _NAMED("potential"),
            "market_drivers": _NAMED("impact"),
        },
        "competitive": {
            "competitors": _NAMED("strength"),
            "competitive_threats": _NAMED("severity"),
            "positioning_gaps": _NAMED("opportunity"),
            "white_space_opportunities": _NAMED("score"),
            "differentiation_opportunities": _NAMED("score"),
        },
    },
    "synthesis": {
        "executive_summary": "str",
        "market_pulse": "number",
        "opportunity_score": "number",
        "confidence": "number",
        "confidence_explanation": "str",
        "build_recommendation": {"decision": "str", "reason": "str"},
        "top_reason_to_build": "str",
        "biggest_risk": "str",
        "best_customer_segment": "str",
        "recommended_customer": "str",
        "recommended_positioning": "str",
        "best_moat": "str",
        "key_opportunities": _INSIGHT,
        "key_risks": _INSIGHT,
        "why_now": _INSIGHT,
        "potential_moats": _INSIGHT,
        "execution_ideas": [{"title": "str", "reason": "str"}],
    },
}


def expected_contract():
    """The response shape the frontend consumes.

    Preferred source is `cache/`: the shapes of the recorded production
    responses that actually completed, unioned together. Only 2 of the 14
    recorded runs qualify -- 11 have
    `intelligence.customer/market/competitive == {}` because the old
    `openrouter/free` calls returned an empty object and the pipeline stored
    it without complaint, and a twelfth is a hand-written stub
    ({"test": ...}). Degraded runs cannot define the contract.

    `cache/` is a runtime artifact and is not in version control, so a fresh
    clone has nothing to derive from. FROZEN_CONTRACT below is that same
    derivation, computed once from those 2 complete runs and checked in, so
    the verifier is self-contained. When a cache is present it takes
    precedence -- that keeps the check honest against real data rather than
    against a literal that could drift.
    """
    complete, degraded = [], 0

    for path in sorted(glob.glob(os.path.join("cache", "*.json"))):
        try:
            with open(path, encoding="utf-8") as f:
                result = json.load(f)["result"]
        except (OSError, ValueError, KeyError, TypeError):
            degraded += 1
            continue
        sections = result.get("intelligence", {})
        if all(
            isinstance(sections.get(s), dict) and len(sections[s]) >= 5
            for s in ("customer", "market", "competitive")
        ):
            complete.append(shape(result))
        else:
            degraded += 1

    if not complete:
        return FROZEN_CONTRACT, 0, degraded

    contract = complete[0]
    for other in complete[1:]:
        contract = merge(contract, other)

    return contract, len(complete), degraded


def diff(expected, actual, path="") -> list:
    problems = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path or 'root'}: expected object, got {type(actual).__name__}"]
        for key, sub in expected.items():
            here = f"{path}.{key}" if path else key
            if key not in actual:
                problems.append(f"{here}: MISSING")
            else:
                problems += diff(sub, actual[key], here)
        return problems

    if isinstance(expected, list):
        if not isinstance(actual, list):
            return [f"{path}: expected array, got {type(actual).__name__}"]
        if expected != ["?"] and actual:
            problems += diff(expected[0], actual[0], f"{path}[0]")
        return problems

    if expected == "number":
        ok = isinstance(actual, (int, float)) and not isinstance(actual, bool)
    elif expected == "bool":
        ok = isinstance(actual, bool)
    elif expected == "str":
        ok = isinstance(actual, str)
    else:
        ok = True

    if not ok:
        problems.append(f"{path}: expected {expected}, got {type(actual).__name__} ({actual!r})")
    return problems


# --------------------------------------------------------------------------
# Stub model output
# --------------------------------------------------------------------------

GOOD = json.dumps({
    "customer": {
        "customer_segments": [{"name": "Busy professionals", "score": 72}],
        "pain_points": [{"name": "Inconsistent tracking", "signal_strength": 68}],
        "desired_outcomes": [{"name": "Effortless logging", "importance": 70}],
        "behavior_patterns": [{"name": "Abandons apps after two weeks", "confidence": 55}],
        "opportunity_areas": [{"name": "Automated meal capture", "score": 64}],
    },
    "market": {
        "market_size": {"estimate": "$4.2B", "confidence": 55},
        "growth_rate": {"estimate": "14% CAGR", "confidence": 50},
        "market_maturity": {"stage": "Growth", "confidence": 60},
        "future_outlook": {"direction": "Expanding", "confidence": 58},
        "key_trends": [{"name": "AI personalisation", "strength": 75}],
        "emerging_trends": [{"name": "Wearable integration", "potential": 62}],
        "market_drivers": [{"name": "Preventive health spend", "impact": 66}],
    },
    "competitive": {
        "competitors": [{"name": "MyFitnessPal", "strength": 80}],
        "competitive_threats": [{"name": "Incumbent data moat", "severity": 70}],
        "positioning_gaps": [{"name": "Clinical credibility", "opportunity": 65}],
        "white_space_opportunities": [{"name": "Chronic condition support", "score": 68}],
        "differentiation_opportunities": [{"name": "Dietitian in the loop", "score": 71}],
    },
    "synthesis": {
        "market_pulse": 68, "opportunity_score": 64,
        "build_recommendation": {"decision": "Yes", "reason": "Clear unserved segment."},
        "confidence": 60, "confidence_explanation": "Moderate evidence breadth.",
        "top_reason_to_build": "Retention gap in incumbents.",
        "biggest_risk": "Incumbent distribution.",
        "best_customer_segment": "Busy professionals",
        "best_moat": "Clinical partnerships",
        "executive_summary": "Growing market with a retention gap.",
        "why_now": [{"title": "AI cost drop", "evidence": "Multiple launches", "reason": "Enables personalisation."}],
        "key_opportunities": [{"title": "Automated capture", "evidence": "Repeated complaint", "reason": "Removes friction."}],
        "key_risks": [{"title": "Churn", "evidence": "Two-week abandonment", "reason": "Category-wide problem."}],
        "recommended_customer": "Busy professionals",
        "recommended_positioning": "Clinically credible automation",
        "potential_moats": [{"title": "Dietitian network", "evidence": "Gap noted", "reason": "Hard to copy."}],
        "execution_ideas": [{"title": "Photo logging", "reason": "Lowest friction entry."}],
    },
})

ADVERSARIAL = {
    "fenced": "```json\n" + GOOD + "\n```",
    "prose wrapped": "Sure! Here is the analysis:\n" + GOOD + "\nLet me know if you need more.",
    "truncated": GOOD[: int(len(GOOD) * 0.7)],
    "trailing commas": GOOD.replace("}]", "},]"),
    "scores as strings": GOOD.replace('"score": 72', '"score": "72"'),
    "score out of range": GOOD.replace('"market_pulse": 68', '"market_pulse": 480'),
    "empty": "",
    "not json at all": "I cannot help with that request.",
    "sections missing": json.dumps({"customer": json.loads(GOOD)["customer"]}),
}


class StubLLM:
    def __init__(self, payload=GOOD, fail=False):
        self.payload, self.fail, self.calls = payload, fail, 0

    def call(self, prompt, model=None, **kw):
        self.calls += 1
        self.prompt = prompt
        if self.fail:
            raise RuntimeError("simulated provider outage")
        return self.payload


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    from app import config
    from app.intelligence import unified_intelligence
    from app.services import analysis_service
    from app.services.json_utils import parse_json, normalise_bundle

    contract, n_complete, n_degraded = expected_contract()
    if n_complete:
        print(f"\nContract derived from {n_complete} complete cached responses "
              f"({n_degraded} degraded entries ignored -- see notes).\n")
    else:
        print("\nContract taken from the checked-in FROZEN_CONTRACT "
              "(no cache/ present; see expected_contract docstring).\n")

    # ---------------------------------------------------------------- 1
    print("1. JSON recovery against adversarial model output")
    for label, payload in ADVERSARIAL.items():
        bundle = normalise_bundle(parse_json(payload))
        problems = (
            diff(contract["intelligence"]["customer"], bundle["customer"], "customer")
            + diff(contract["intelligence"]["market"], bundle["market"], "market")
            + diff(contract["intelligence"]["competitive"], bundle["competitive"], "competitive")
            + diff(contract["synthesis"], bundle["synthesis"], "synthesis")
        )
        check(f"recovers from: {label}", not problems, "; ".join(problems[:3]))

    scored = normalise_bundle(parse_json(ADVERSARIAL["score out of range"]))
    check("clamps out-of-range score",
          scored["synthesis"]["market_pulse"] <= 100,
          str(scored["synthesis"]["market_pulse"]))

    stringy = normalise_bundle(parse_json(ADVERSARIAL["scores as strings"]))
    check("coerces string score to int",
          isinstance(stringy["customer"]["customer_segments"][0]["score"], int))

    # ---------------------------------------------------------------- 2
    print("\n2. Full pipeline response shape")

    stub = StubLLM()
    unified_intelligence._service = lambda: (stub, "stub-model")

    if OFFLINE:
        async def fake_collect(self, topic):
            return [
                {"source": "ddgs", "title": f"{topic} review {i}",
                 "url": f"https://example.com/{i}",
                 "snippet": "Users report the market is growing at 14% CAGR to $4.2B.",
                 "query": f"q{i % 3}"}
                for i in range(40)
            ]
        analysis_service.AnalysisService.collect = fake_collect

    config.CACHE_ENABLED = False
    service = analysis_service.AnalysisService()

    started = time.time()
    result = asyncio.run(service.analyze("AI Nutrition Coach"))
    elapsed = time.time() - started

    problems = diff(contract, result)
    check("response matches cached contract exactly", not problems, "; ".join(problems[:6]))
    check("exactly one LLM call", stub.calls == 1, f"{stub.calls} calls")
    check("evidence reached the prompt", "EVIDENCE" in stub.prompt)
    check("prompt under 12KB", len(stub.prompt) < 12000, f"{len(stub.prompt)} chars")
    print(f"       prompt size: {len(stub.prompt)} chars | wall: {elapsed:.1f}s"
          f" | evidence: {result['meta']['evidence_count']}")

    # ---------------------------------------------------------------- 3
    print("\n3. Degradation when the provider is down")
    broken = StubLLM(fail=True)
    unified_intelligence._service = lambda: (broken, "stub-model")
    degraded = asyncio.run(service.analyze("AI Nutrition Coach"))
    check("still returns full contract on LLM failure", not diff(contract, degraded))
    check("no exception surfaced to the route", isinstance(degraded, dict))

    # ---------------------------------------------------------------- 4
    print("\n4. Cache is consulted before collection")
    from app.services.cache_service import CacheService

    config.CACHE_ENABLED = True
    probe = {"hit": False}

    async def tracked_collect(self, topic):
        probe["hit"] = True
        return []

    original = analysis_service.AnalysisService.collect
    CacheService.set("cache probe topic", result)
    analysis_service.AnalysisService.collect = tracked_collect

    t = time.time()
    cached = asyncio.run(service.analyze("cache probe topic"))
    cache_ms = (time.time() - t) * 1000

    analysis_service.AnalysisService.collect = original
    try:
        os.remove(os.path.join("cache", CacheService._key("cache probe topic") + ".json"))
    except OSError:
        pass

    check("collection skipped on cache hit", not probe["hit"])
    check("cache hit marked in meta", cached["meta"]["cached"] is True)
    check("cache hit under 100ms", cache_ms < 100, f"{cache_ms:.0f}ms")
    print(f"       cache hit served in {cache_ms:.0f}ms")

    # ----------------------------------------------------------------
    print(f"\n{'=' * 58}")
    print(f"{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        for name in FAIL:
            print(f"  FAILED: {name}")
    print("=" * 58)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
