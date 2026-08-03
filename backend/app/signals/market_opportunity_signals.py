"""Market-opportunity signals: figures pulled straight out of the evidence text.

This module used to open with `if item.get("source") != "market_report": continue`,
and nothing in the pipeline has ever emitted `market_report` evidence --
`MarketReportsCollector` exists but is imported nowhere. So the loop body never
ran once, and every field below was hardcoded to zero by accident. The prompt
builder had even grown a special case to strip the resulting empty lists before
they were serialised.

The filter is gone. Two ways to fix it were measured:

  wire in MarketReportsCollector   +3.8s   (6.3s -> 10.1s collection)
  drop the filter                  +0.0s

The dedicated collector runs six more DDGS searches, and DDGS is already the
critical path at eight -- fourteen concurrent searches throttle each other, so
the whole batch slows down rather than the new work overlapping for free. It
also displaced real evidence: the ranked 30 went from 24 search results to 16.

Dropping the filter costs nothing because the figures were always there. The
default query list already includes "{topic} market size growth forecast" and
"{topic} industry report CAGR", so those market reports were being collected,
ranked and fed to the model the whole time -- just never measured. Verified on
three topics: opportunity_score 0 -> 100 / 71 / 100, with real figures.
"""

import re

# A currency amount with a scale word or suffix: "$1.9 billion", "$400m".
_MONEY = re.compile(r"\$\d+(?:\.\d+)?\s*(?:billion|million|b|m)\b", re.IGNORECASE)

# Any percentage. Deliberately broad, but see the gate in the loop below.
_PERCENT = re.compile(r"\d+(?:\.\d+)?%")

# A percentage is only a *growth* rate if the item is talking about growth.
# Without this gate the field fills with discount percentages, survey results
# and accuracy claims -- measured examples included "93%" and "99.9%".
_GROWTH_CONTEXT = ("cagr", "growth", "growing", "forecast", "projected",
                   "expected to reach", "annually", "per year", "yoy")

_BILLION_SUFFIX = re.compile(r"\$\d+(?:\.\d+)?\s*b\b")
_MILLION_SUFFIX = re.compile(r"\$\d+(?:\.\d+)?\s*m\b")


def extract(evidence):
    market_size_mentions = 0
    growth_mentions = 0
    forecast_mentions = 0
    cagr_mentions = 0
    billion_mentions = 0
    million_mentions = 0

    # dict.fromkeys semantics: dedupe while keeping first-seen order, which is
    # evidence-rank order. The previous code used list(set(...)), whose
    # iteration order changes between processes because string hashing is
    # salted -- so the same response could come back with these arrays
    # reordered, which is visible once a UI renders them.
    detected_market_sizes = {}
    detected_growth_rates = {}

    for item in evidence:
        text = (
            (item.get("title") or "") + " " + (item.get("snippet") or "")
        ).lower()

        if not text.strip():
            continue

        for match in _MONEY.findall(text):
            detected_market_sizes[match.strip()] = None

        if any(term in text for term in _GROWTH_CONTEXT):
            for match in _PERCENT.findall(text):
                detected_growth_rates[match.strip()] = None

        if "market size" in text:
            market_size_mentions += 1

        if "growth" in text or "growing" in text or "expansion" in text:
            growth_mentions += 1

        if ("forecast" in text or "projected" in text
                or "expected to reach" in text or "predicted" in text):
            forecast_mentions += 1

        if "cagr" in text:
            cagr_mentions += 1

        if "billion" in text or _BILLION_SUFFIX.search(text):
            billion_mentions += 1

        if "million" in text or _MILLION_SUFFIX.search(text):
            million_mentions += 1

    # `opportunity_score` used to be returned here as
    #     min(100, size*10 + growth*8 + forecast*10 + cagr*12 + billion*15 + million*5)
    # and was removed in session 4 rather than repaired.
    #
    # Those weights were written when the loop above was gated to
    # `market_report` sources, of which there would have been a handful.
    # Removing that dead filter widened the input from zero items to all 30
    # ranked ones and the weights were never re-tuned, so the sum cleared 100
    # on ordinary inputs and the clamp did the rest. Measured on "Developer
    # tools for edge functions": 2*10 + 7*8 + 2*10 + 2*12 + 1*15 + 1*5 = 140,
    # clamped to 100.
    #
    # A composite that saturates is not measuring anything, and there was no
    # defensible scale underneath it -- nothing makes a CAGR mention worth 12
    # of whatever a "billion" mention is worth 15 of. The counts below are the
    # finding; the weighted sum only obscured them.
    return {
        "market_size_mentions": market_size_mentions,
        "growth_mentions": growth_mentions,
        "forecast_mentions": forecast_mentions,
        "cagr_mentions": cagr_mentions,
        "billion_mentions": billion_mentions,
        "million_mentions": million_mentions,
        # The denominator. Without it a count of 7 is unreadable -- 7 of 8 and
        # 7 of 200 are opposite findings.
        "sources_scanned": len(evidence),
        "detected_market_sizes": list(detected_market_sizes),
        "detected_growth_rates": list(detected_growth_rates),
    }
