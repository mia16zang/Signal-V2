"""Tests for the sizing-claim extractor.

The point of the module is that it refuses to publish a figure the sources did
not state. These tests are mostly about the refusals.

    python test_sizing.py
"""

import sys

from app.payload.sizing import (
    build_market_sizing,
    format_usd,
    parse_usd,
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
    {"id": "e1", "display_name": "Web search", "url": "https://gartner.com/x",
     "title": "Edge market to hit $9.75 billion by 2029",
     "snippet": "Analysts expect growth."},
    {"id": "e2", "display_name": "Web search", "url": "https://statista.com/y",
     "title": "Developer tooling", "snippet": "The segment was worth $496.1m in 2024."},
    {"id": "e3", "display_name": "YouTube", "url": "https://youtube.com/z",
     "title": "Tutorial", "snippet": "No figures here."},
]


def claim(eid, figure, year=None, scope=""):
    return {"evidence_id": eid, "figure_text": figure, "year": year, "scope": scope}


def main():
    print("\n1. Parsing figures")
    eq("billions", parse_usd("$9.75 billion"), 9.75e9)
    eq("million suffix", parse_usd("$496.1m"), 4.961e8)
    eq("bn suffix", parse_usd("USD 234.70bn"), 234.7e9)
    eq("comma separated", parse_usd("$1,200 million"), 1.2e9)
    eq("no figure returns None", parse_usd("a big market"), None)
    eq("empty returns None", parse_usd(""), None)
    eq("formats billions", format_usd(9.8e9), "$9.8B")
    eq("formats millions", format_usd(4.961e8), "$500M")

    print("\n2. Nothing found is a legitimate answer")
    none = build_market_sizing({"claims": []}, EVIDENCE)
    eq("no claims", none.claims, [])
    ok("says so plainly", "No sizing figures" in none.display, none.display)
    ok("no number is invented anywhere",
       none.low_usd is None and none.high_usd is None)
    ok("basis states how many sources were scanned", "3 sources" in none.basis,
       none.basis)

    print("\n3. Unverifiable claims are dropped, not repaired")
    bogus = build_market_sizing({"claims": [
        claim("e99", "$5 billion"),                 # id does not exist
        claim("e3", "$7.2 billion"),                # source says no such thing
        claim("e1", "$12 billion"),                 # wrong figure for that source
    ]}, EVIDENCE)
    eq("every unverifiable claim is dropped", bogus.claims, [])
    ok("and nothing is published in their place",
       "No sizing figures" in bogus.display, bogus.display)

    print("\n4. A single verified claim is attributed")
    one = build_market_sizing({"claims": [
        claim("e1", "$9.75 billion", 2029, "Edge functions platform, global"),
    ]}, EVIDENCE)
    eq("one claim survives", len(one.claims), 1)
    eq("figure is kept verbatim", one.claims[0].figure_text, "$9.75 billion")
    eq("value is parsed server-side", one.claims[0].value_usd, 9.75e9)
    eq("scope is carried", one.claims[0].scope, "Edge functions platform, global")
    ok("the source is named in the display", "gartner.com" in one.display, one.display)
    ok("a lone claim counts as converged", one.converges is True)

    print("\n5. Divergent claims are reported as divergent")
    both = build_market_sizing({"claims": [
        claim("e1", "$9.75 billion", 2029),
        claim("e2", "$496.1m", 2024),
    ]}, EVIDENCE)
    eq("both verified", len(both.claims), 2)
    eq("low", both.low_usd, 4.961e8)
    eq("high", both.high_usd, 9.75e9)
    ok("19.7x apart does not converge", both.converges is False)
    ok("display says they do not converge",
       "do not converge" in both.display, both.display)
    ok("display carries both ends",
       "$500M" in both.display and "$9.8B" in both.display, both.display)
    ok("differing years are flagged as not comparable",
       "different years" in both.basis, both.basis)

    print("\n6. Close claims converge")
    near = build_market_sizing({"claims": [
        claim("e1", "$9.75 billion"),
        claim("e2", "$496.1m"),
    ]}, [
        EVIDENCE[0],
        {"id": "e2", "display_name": "Web search", "url": "https://x.com/y",
         "title": "", "snippet": "worth $496.1m"},
    ])
    ok("still divergent at 19.7x", near.converges is False)

    tight = build_market_sizing({"claims": [
        claim("e1", "$9.75 billion"),
        claim("e2", "$9.75 billion"),
    ]}, [
        EVIDENCE[0],
        {"id": "e2", "display_name": "Web search", "url": "https://x.com/y",
         "title": "", "snippet": "also $9.75 billion"},
    ])
    eq("identical figures deduplicate to one claim", len(tight.claims), 1)

    print("\n7. Scope matching")
    from app.payload.sizing import build_market_growth

    SCOPED = [
        {"id": "e1", "display_name": "Web search", "url": "https://a.com/1",
         "title": "", "snippet": "The global SaaS market reaches $195.8 billion."},
        {"id": "e2", "display_name": "Web search", "url": "https://b.com/2",
         "title": "", "snippet": "Global SaaS hits $307.3 billion by 2030."},
        {"id": "e3", "display_name": "Web search", "url": "https://c.com/3",
         "title": "", "snippet": "HR SaaS specifically is worth $12.4 billion."},
    ]

    mixed = build_market_sizing({"claims": [
        {"evidence_id": "e1", "figure_text": "$195.8 billion",
         "scope": "global SaaS market", "scope_match": "broader"},
        {"evidence_id": "e2", "figure_text": "$307.3 billion",
         "scope": "global SaaS market", "scope_match": "broader"},
        {"evidence_id": "e3", "figure_text": "$12.4 billion",
         "scope": "HR SaaS", "scope_match": "exact"},
    ]}, SCOPED)

    eq("every claim carries a scope_match",
       [c.scope_match for c in mixed.claims], ["broader", "broader", "exact"])
    eq("all three claims are still published", len(mixed.claims), 3)
    eq("the range is computed from the exact-scope claim only",
       (mixed.low_usd, mixed.high_usd), (12.4e9, 12.4e9))
    eq("and says which scope it used", mixed.range_scope, "exact")
    ok("the excluded broader claims are accounted for",
       "different scope" in mixed.basis, mixed.basis)

    broader_only = build_market_sizing({"claims": [
        {"evidence_id": "e1", "figure_text": "$195.8 billion",
         "scope": "global SaaS market", "scope_match": "broader"},
        {"evidence_id": "e2", "figure_text": "$307.3 billion",
         "scope": "global SaaS market", "scope_match": "broader"},
    ]}, SCOPED)
    eq("with no exact claims the broader ones are still shown",
       len(broader_only.claims), 2)
    ok("but the display says they describe a wider category",
       "broader than the topic" in broader_only.display, broader_only.display)

    print("\n8. Growth claims are extracted, not generated")
    GROWTH_EV = [
        {"id": "e8", "display_name": "Web search", "url": "https://a.com/8",
         "title": "", "snippet": "HR SaaS grows at 13.7% CAGR through 2030."},
        {"id": "e20", "display_name": "Web search", "url": "https://b.com/20",
         "title": "", "snippet": "HR software CAGR 10.60% over the period."},
    ]
    g = build_market_growth({"growth_claims": [
        {"evidence_id": "e8", "figure_text": "13.7% CAGR", "scope": "HR SaaS",
         "scope_match": "exact", "period": "2025-2030"},
        {"evidence_id": "e20", "figure_text": "10.60%", "scope": "HR software",
         "scope_match": "exact"},
    ]}, GROWTH_EV)
    eq("both rates verified", len(g.claims), 2)
    eq("parsed from the quoted text", (g.low_pct, g.high_pct), (10.6, 13.7))
    ok("3.1 points apart converges", g.converges is True)
    ok("the range reflects what sources said, not a round number",
       "10.6%" in g.display and "13.7%" in g.display, g.display)

    none_stated = build_market_growth({"growth_claims": []}, GROWTH_EV)
    eq("no rate stated is a legitimate answer", none_stated.claims, [])
    ok("and says so", "No growth figure" in none_stated.display,
       none_stated.display)

    print("\n9. Malformed input does not raise")
    for bad in (None, {}, {"claims": None}, {"claims": ["string"]},
                {"claims": [{"evidence_id": None}]}):
        result = build_market_sizing(bad, EVIDENCE)
        ok(f"survives {str(bad)[:28]}", result.claims == [])

    print()
    if failures:
        print(f"{len(failures)} FAILED: {', '.join(failures)}")
        return 1
    print("all sizing tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
