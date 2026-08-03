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

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load any real .env FIRST. These stubs exist so the services can be
# constructed without credentials -- but load_dotenv does not override
# variables that are already set, so setting them first would mask the real
# keys for anything else running in the same process. The LLM is stubbed
# either way, so a real key present here is never spent.
load_dotenv()
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
        "evidence_count": "number",
        "evidence_used": "number",
    },
    # Additive: the ranked evidence the analysis was built from. Asserted here
    # so a future change cannot quietly drop it again -- the frontend cites it.
    "evidence": [{
        "rank": "number",
        "source": "str",
        "title": "str",
        "url": "str",
        "snippet": "str",
        "query": "str",
        "used_in_prompt": "bool",
    }],
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

def _row(name, score_key, score, ids=("e1",)):
    return {"name": name, score_key: score, "detail": f"{name} — drawer copy.",
            "evidence_ids": list(ids)}


def _ins(title, score, ids=("e1",)):
    return {"title": title, "score": score, "evidence": "Noted in sources",
            "reason": "Short reason.", "evidence_ids": list(ids)}


# A compliant reply: every score on the declared 90/75/50 scale and every item
# citing at least one evidence id. `recommended_customer` and
# `best_customer_segment` are deliberately identical -- that is the duplicate
# the headline de-duplication is supposed to catch.
GOOD = json.dumps({
    "customer": {
        "customer_segments": [_row("Busy professionals", "score", 90)],
        "pain_points": [_row("Inconsistent tracking", "signal_strength", 75)],
        "desired_outcomes": [_row("Effortless logging", "importance", 75)],
        "behavior_patterns": [_row("Abandons apps after two weeks", "confidence", 50)],
        "opportunity_areas": [_row("Automated meal capture", "score", 75)],
    },
    "market": {
        "market_size": {"estimate": "$4.23B", "confidence": 75},
        "growth_rate": {"estimate": "14.4% CAGR", "confidence": 50},
        "market_maturity": {"stage": "Growth", "confidence": 90},
        "future_outlook": {"direction": "Expanding", "confidence": 75},
        "key_trends": [_row("AI personalisation", "strength", 75)],
        "emerging_trends": [_row("Wearable integration", "potential", 50)],
        "market_drivers": [_row("Preventive health spend", "impact", 90)],
    },
    "competitive": {
        "competitors": [_row("MyFitnessPal", "strength", 90)],
        "competitive_threats": [_row("Incumbent data moat", "severity", 75)],
        "positioning_gaps": [_row("Clinical credibility", "opportunity", 75)],
        "white_space_opportunities": [_row("Chronic condition support", "score", 50)],
        "differentiation_opportunities": [_row("Dietitian in the loop", "score", 75)],
    },
    "synthesis": {
        "build_recommendation": {"decision": "Yes", "reason": "Clear unserved segment."},
        "confidence": 75, "confidence_explanation": "Moderate evidence breadth.",
        "top_reason_to_build": "Retention gap in incumbents.",
        "biggest_risk": "Incumbent distribution.",
        "best_customer_segment": "Busy professionals",
        "best_moat": "Clinical partnerships",
        "executive_summary": "Growing market with a retention gap.",
        "why_now": [_ins("AI cost drop", 90)],
        "key_opportunities": [_ins("Automated capture", 75)],
        "key_risks": [_ins("Churn", 75)],
        "recommended_customer": "Busy professionals",
        "recommended_positioning": "Clinically credible automation",
        "potential_moats": [_ins("Dietitian network", 50)],
        "execution_ideas": [{"title": "Photo logging", "score": 75,
                             "reason": "Lowest friction entry.",
                             "evidence_ids": ["e1"]}],
    },
})

# The same reply with both rules broken: an off-scale score and no citations.
NON_COMPLIANT = (
    GOOD.replace('"score": 90', '"score": 64')
        .replace('"evidence_ids": ["e1"]', '"evidence_ids": []')
)

ADVERSARIAL = {
    "fenced": "```json\n" + GOOD + "\n```",
    "prose wrapped": "Sure! Here is the analysis:\n" + GOOD + "\nLet me know if you need more.",
    "truncated": GOOD[: int(len(GOOD) * 0.7)],
    "trailing commas": GOOD.replace("}]", "},]"),
    "scores as strings": GOOD.replace('"score": 90', '"score": "90"'),
    "score out of range": GOOD.replace('"confidence": 75', '"confidence": 480'),
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
          scored["synthesis"]["confidence"] <= 100,
          str(scored["synthesis"]["confidence"]))

    stringy = normalise_bundle(parse_json(ADVERSARIAL["scores as strings"]))
    check("coerces string score to int",
          isinstance(stringy["customer"]["customer_segments"][0]["score"], int))

    long_label = json.dumps({"customer": {"customer_segments": [
        {"name": " ".join(f"word{i}" for i in range(20)), "score": 90}]}})
    capped = normalise_bundle(parse_json(long_label))
    check("caps a list label at 10 words",
          len(capped["customer"]["customer_segments"][0]["name"].split()) <= 11,
          capped["customer"]["customer_segments"][0]["name"])

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
    # A compliant reply must cost exactly one call. The corrective retry is
    # conditional, and a retry that fired on every request would quietly undo
    # the whole point of merging four calls into one.
    check("exactly one LLM call on a compliant reply", stub.calls == 1,
          f"{stub.calls} calls")
    check("evidence reached the prompt", "EVIDENCE" in stub.prompt)
    check("prompt under 12KB", len(stub.prompt) < 12000, f"{len(stub.prompt)} chars")
    print(f"       prompt size: {len(stub.prompt)} chars | wall: {elapsed:.1f}s"
          f" | evidence: {result['meta']['evidence_count']}")

    # ------------------------------------------------------------- 2b
    print("\n2b. Off-scale scores and missing citations trigger one retry")

    bad = StubLLM(payload=NON_COMPLIANT)
    unified_intelligence._service = lambda: (bad, "stub-model")
    retried = asyncio.run(service.analyze("AI Nutrition Coach retry"))

    check("retries exactly once, not repeatedly", bad.calls == 2, f"{bad.calls} calls")
    check("still returns full contract after a failed retry",
          not diff(contract, retried))

    scores = [
        item["score"]
        for lst in retried["report"]["lists"].values()
        for item in lst["items"]
    ]
    check("off-scale scores are snapped onto the declared scale",
          all(s in (90, 75, 50) for s in scores), str(sorted(set(scores))))

    # ---------------------------------------------------------------- 3
    print("\n3. Degradation when the provider is down")
    broken = StubLLM(fail=True)
    unified_intelligence._service = lambda: (broken, "stub-model")
    degraded = asyncio.run(service.analyze("AI Nutrition Coach"))
    check("still returns full contract on LLM failure", not diff(contract, degraded))
    check("no exception surfaced to the route", isinstance(degraded, dict))

    # The failure has to be *legible*. Returning the empty contract quietly is
    # what let a provider outage reach the reader as a "Monitor" verdict.
    check("total failure is flagged degraded", degraded.get("degraded") is True)
    check("degraded carries a reason", bool(degraded.get("degraded_reason")),
          str(degraded.get("degraded_reason")))
    check("total failure is flagged analysis_failed",
          degraded.get("analysis_failed") is True)
    check("v2 verdict refuses to state a decision it does not have",
          degraded["report"]["verdict"]["decision"] is None,
          str(degraded["report"]["verdict"]["decision"]))
    check("v2 verdict says why",
          bool(degraded["report"]["verdict"]["decision_unavailable_reason"]))
    check("v1 verdict keeps its default so the live page still renders",
          degraded["synthesis"]["build_recommendation"]["decision"] == "Monitor")

    # A transient outage must not become a lasting one.
    from app.services.cache_service import CacheService as _Cache

    config.CACHE_ENABLED = True
    asyncio.run(service.analyze("poison probe topic"))
    check("a failed briefing is not written to the cache",
          _Cache.get("poison probe topic") is None,
          "an empty briefing was cached and would be served for CACHE_TTL_HOURS")
    config.CACHE_ENABLED = False

    # And the route turns it into an error rather than a 200.
    from fastapi import HTTPException

    from app.models.analysis import AnalysisRequest
    from app.routes import analyze as analyze_route

    analyze_route.service = service
    try:
        asyncio.run(analyze_route.analyze(AnalysisRequest(topic="AI Nutrition Coach")))
        check("route returns an error when there is no briefing", False,
              "route returned 200 with an empty briefing")
    except HTTPException as e:
        check("route returns 503 when there is no briefing", e.status_code == 503,
              f"status {e.status_code}")
        check("route explains why and says it is retryable",
              isinstance(e.detail, dict) and e.detail.get("retryable") is True)
        check("the client-facing 503 body carries no raw provider JSON",
              "RESOURCE_EXHAUSTED" not in json.dumps(e.detail)
              and "quotaMetric" not in json.dumps(e.detail),
              json.dumps(e.detail)[:200])

    # A rate limit replayed through the real client path, verbatim as Gemini
    # sent it. The raw body belongs in the log; the response gets the
    # classified phrase and the retry window, nothing else.
    from app.services.gemini_service import GeminiService, LLMUnavailable, quota_detail

    RAW_429 = (
        "429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded "
        "your current quota.', 'details': [{'@type': 'QuotaFailure', 'violations': "
        "[{'quotaId': 'GenerateRequestsPerMinutePerProjectPerModel-FreeTier', "
        "'quotaValue': '5'}]}, {'retryDelay': '33s'}]}}"
    )

    detail = quota_detail(Exception(RAW_429))
    check("the violated quota is parsed out of the raw body",
          "quotaValue" in detail or "limit=5" in detail, detail)
    check("the retry window is parsed out of the raw body",
          "retryDelay=33" in detail, detail)

    class _Quota429:
        def generate_content(self, **kw):
            raise Exception(RAW_429)

    saved_client = GeminiService._client
    GeminiService._client = type("C", (), {"models": _Quota429()})()
    try:
        GeminiService().call("x")
        check("a rate limit raises", False, "no exception")
    except LLMUnavailable as e:
        check("a rate limit fails fast rather than retrying a 33s window",
              e.retryable is False)
        check("the retry window reaches the caller", e.retry_after == 33.0,
              str(e.retry_after))
        check("the client-safe reason is short and readable",
              len(e.reason) < 60 and "RESOURCE_EXHAUSTED" not in e.reason, e.reason)
        check("the raw body is kept on the exception for the log",
              "RESOURCE_EXHAUSTED" in str(e))
    finally:
        GeminiService._client = saved_client

    # Non-fatal provider errors are still retried; fatal ones are not.
    from app.services.gemini_service import classify

    # A 429 body routinely carries three-digit numbers that are not status
    # codes -- a quota value, a limit, a docs URL. Matching those as bare
    # substrings classified a rate limit as a fatal rejection, which was
    # observed live: four identical requests, three rate limits and one
    # spurious "request rejected by the provider".
    for label, body in (
        ("limit: 400 in the message",
         "429 RESOURCE_EXHAUSTED {'message': 'limit: 400'} {'retryDelay': '50s'}"),
        ("a docs URL ending 404",
         "429 RESOURCE_EXHAUSTED https://x.dev/e/404 {'retryDelay': '50s'}"),
        ("a quotaValue of 401",
         "429 RESOURCE_EXHAUSTED {'quotaValue': '401'} {'retryDelay': '50s'}"),
    ):
        retryable, wait, reason = classify(Exception(body))
        check(f"a 429 carrying {label} is still read as a rate limit",
              "rate limited" in reason and wait == 50.0, reason)

    check("a structured 403 is a rejection, not a rate limit",
          classify(Exception("{'error': {'code': 403, 'message': 'PERMISSION_DENIED'}}"))[2]
          == "request rejected by the provider")

    check("an exhausted quota is not retried",
          classify(Exception("429 RESOURCE_EXHAUSTED quota")) [0] is False)
    check("a rate limit with a short delay is retried",
          classify(Exception("429 RESOURCE_EXHAUSTED {'retryDelay': '3s'}"))[0] is True)
    check("a bad api key is not retried",
          classify(Exception("400 INVALID_ARGUMENT API key not valid"))[0] is False)
    check("an unknown error is retried",
          classify(Exception("503 backend unavailable"))[0] is True)

    # ------------------------------------------------------------- 3b
    print("\n3b. Landing-page suggestions are served without the provider")

    from app.services.cache_service import CacheService as _Seed

    config.CACHE_ENABLED = True
    counting = StubLLM(fail=True)
    unified_intelligence._service = lambda: (counting, "stub-model")

    seeds = sorted(_Seed.SEED_DIR.glob("*.json")) if _Seed.SEED_DIR.exists() else []
    check("seed briefings are checked in", len(seeds) >= 4, f"{len(seeds)} found")

    if seeds:
        topics = [json.load(open(p, encoding="utf-8"))["topic"] for p in seeds]
        served = [asyncio.run(service.analyze(t)) for t in topics]

        check("every suggestion is served without an LLM call",
              counting.calls == 0, f"{counting.calls} calls made")
        check("every suggestion returns a real briefing",
              all(s["synthesis"]["executive_summary"] for s in served))
        check("every suggestion matches the contract",
              all(not diff(contract, s) for s in served))
        check("seeded responses say they are seeded",
              all(s["meta"].get("seeded") for s in served))
        check("seeded responses keep their real capture time",
              all(s["meta"].get("generated_at") for s in served))
        check("no seeded briefing is a failed one",
              not any(s.get("analysis_failed") or s.get("degraded") for s in served))

    config.CACHE_ENABLED = False

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
