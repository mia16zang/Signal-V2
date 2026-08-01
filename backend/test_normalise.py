"""Unit tests for the normalisation layer.

No network, no model, no fixture. These cover the rules that a single captured
response cannot exercise -- most importantly the low-confidence suppression,
which does not fire on the sample in fixtures/after.json because that response
happened to come back with confidence 75.

    python test_normalise.py
"""

import sys

from app.payload.normalise import (
    MIN_REPORTABLE_CONFIDENCE,
    build_insight_list,
    dedupe_headlines,
    evidence_summary,
    market_estimate,
    round_currency,
    round_percentages,
    round_sig,
    signal_estimate,
    tidy_figures,
)

failures = []


def eq(name, got, want):
    ok = got == want
    print(f"  {'[PASS]' if ok else '[FAIL]'} {name}"
          + ("" if ok else f" -- got {got!r}, want {want!r}"))
    if not ok:
        failures.append(name)


def ok(name, condition, detail=""):
    print(f"  {'[PASS]' if condition else '[FAIL]'} {name}"
          + ("" if condition else f" -- {detail}"))
    if not condition:
        failures.append(name)


EVIDENCE = [
    {"rank": 1, "source": "ddgs", "title": "Market size to hit $9.75 billion",
     "snippet": "CAGR of 27.6%", "used_in_prompt": True},
    {"rank": 2, "source": "youtube", "title": "Tutorial", "snippet": "how to",
     "used_in_prompt": True},
    {"rank": 3, "source": "ddgs", "title": "Review", "snippet": "good",
     "used_in_prompt": False},
]
for e in EVIDENCE:
    e["id"] = f"e{e['rank']}"
    e["source_key"] = e["source"]


def main():
    print("\n1. Rounding")
    eq("two sig figs rounds up", round_sig(9.75, 2), 9.8)
    eq("two sig figs on hundreds", round_sig(496.1, 2), 500)
    eq("two sig figs leaves 4.5", round_sig(4.5, 2), 4.5)
    eq("zero survives", round_sig(0), 0)
    eq("percentages become whole", round_percentages("27.6% and 7%"), "28% and 7%")
    eq("currency to two sig figs", round_currency("$9.75 billion by 2029"),
       "$9.8 billion by 2029")
    eq("USD prefix handled", round_currency("USD 234.70bn"), "USD 230 bn")
    eq("tidy does both", tidy_figures("$496.1m growing 27.6%"), "$500 m growing 28%")

    print("\n2. Low-confidence suppression")
    weak = market_estimate({"estimate": "$496.1m", "confidence": 50},
                           "estimate", "market size", EVIDENCE)
    ok("value is dropped below the threshold", weak.value is None, weak.value)
    ok("display explains why", "estimable" in weak.display.lower(), weak.display)
    ok("confidence is retained for context", weak.confidence == 50)
    ok("band is low", weak.confidence_band == "low")
    ok("basis names the threshold",
       str(MIN_REPORTABLE_CONFIDENCE) in weak.basis, weak.basis)

    strong = market_estimate({"estimate": "$9.75 billion", "confidence": 75},
                             "estimate", "market size", EVIDENCE)
    eq("above the threshold the figure survives, rounded",
       strong.value, "$9.8 billion")
    ok("supporting ids are real", set(strong.evidence_ids) <= {e["id"] for e in EVIDENCE})

    empty = market_estimate({"estimate": "", "confidence": 90},
                            "estimate", "market size", EVIDENCE)
    ok("an empty estimate is not collected", empty.collected is False)

    print("\n3. Null is not zero")
    # Product Hunt contributed nothing to EVIDENCE, so `launches` was never
    # measured -- the case a bare 0 cannot distinguish.
    never = signal_estimate("competitive", "launches", 0, EVIDENCE)
    ok("uncollected signal has no value", never.value is None)
    eq("uncollected signal displays an em-dash", never.display, "—")
    ok("uncollected signal says so", never.collected is False)
    ok("basis distinguishes it from a measured zero",
       "never measured" in never.basis, never.basis)

    measured = signal_estimate("customer", "comment_volume", 0, EVIDENCE)
    ok("a genuine zero from a live collector stays a zero",
       measured.value == 0 and measured.collected is True,
       f"{measured.value} / {measured.collected}")

    # trend_growth feeds from Google Trends, so it needs a Trends item present
    # before it counts as measured at all.
    with_trends = EVIDENCE + [{"id": "e4", "rank": 4, "source": "google_trends",
                               "source_key": "google_trends", "title": "",
                               "snippet": "", "used_in_prompt": True}]
    ok("trend growth is unmeasured without a Trends item",
       signal_estimate("virality", "trend_growth", 76.67, EVIDENCE).value is None)

    pct = signal_estimate("virality", "trend_growth", 76.67, with_trends)
    eq("percentage signal is rounded and marked approximate", pct.display, "~77%")
    eq("percentage signal cites the Trends item", pct.evidence_ids, ["e4"])

    print("\n4. Headline de-duplication")
    out = dedupe_headlines({
        "recommended_customer": "Web developers using React and Next.js",
        "best_customer_segment": "Web developers using React and Next.js.",
        "recommended_positioning": "The fastest edge debugger on the market",
        "best_moat": "Proprietary debugging engine",
    })
    ok("first of a duplicate pair survives",
       out["recommended_customer"]["value"] is not None)
    ok("second is suppressed", out["best_customer_segment"]["value"] is None)
    eq("suppression names the original",
       out["best_customer_segment"]["suppressed_reason"],
       "duplicate of recommended_customer")
    ok("genuinely different fields survive",
       out["recommended_positioning"]["value"] and out["best_moat"]["value"])

    print("\n5. Insight lists")
    lst = build_insight_list("pain_points", [
        {"name": "Low", "signal_strength": 50, "evidence_ids": ["e1"]},
        {"name": "High", "signal_strength": 90, "evidence_ids": ["e1"]},
        {"name": "Mid two sources", "signal_strength": 75, "evidence_ids": ["e1", "e2"]},
        {"name": "Mid one source", "signal_strength": 75, "evidence_ids": ["e1"]},
        {"name": "Invented citation", "signal_strength": 90, "evidence_ids": ["e99"]},
    ], "signal_strength", EVIDENCE)

    eq("sorted by score then evidence count",
       [i.label for i in lst.items],
       ["High", "Invented citation", "Mid two sources", "Mid one source", "Low"])
    eq("ranks are assigned after sorting", [i.rank for i in lst.items], [1, 2, 3, 4, 5])
    eq("dangling citations are dropped",
       lst.items[1].evidence_ids, [])
    eq("bands follow scores",
       [i.score_band for i in lst.items],
       ["high", "high", "moderate", "moderate", "low"])
    eq("sort_basis is stated", lst.sort_basis,
       "Score, then number of supporting sources")

    snapped = build_insight_list("key_trends", [
        {"name": "Off scale", "strength": 64, "evidence_ids": ["e1"]},
    ], "strength", EVIDENCE)
    eq("an off-scale score snaps to the nearest band", snapped.items[0].score, 75)

    print("\n6. Evidence counts")
    summary = evidence_summary(EVIDENCE)
    eq("counts reconcile", summary, {"collected": 3, "used": 2, "excluded": 1})

    print()
    if failures:
        print(f"{len(failures)} FAILED: {', '.join(failures)}")
        return 1
    print("all normalisation tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
