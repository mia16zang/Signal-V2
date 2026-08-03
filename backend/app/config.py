"""Central tuning knobs for the analysis pipeline.

Everything that trades speed against completeness lives here so the two
pipeline modes stay honest about what they give up.

PORTFOLIO_MODE = True   -> demo settings. One LLM call, concurrent collection,
                           no Google Trends, no Product Hunt. ~15-20s cold.
PORTFOLIO_MODE = False  -> the original behaviour. Four sequential LLM calls,
                           all four collectors. ~100s cold.

Every value can be overridden with an environment variable so the deployed
demo can be retuned without a redeploy of code.
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------
# Mode
# --------------------------------------------------------------------------

PORTFOLIO_MODE = _flag("PORTFOLIO_MODE", True)


# --------------------------------------------------------------------------
# Collection
# --------------------------------------------------------------------------

# Re-measured 2026-07-29 from a residential IP: 1.0-1.1s, returning a real
# growth_rate on every one of three runs. The earlier note here said 7.4s to a
# 429, which was measured against a cloud IP -- so the failure mode is real but
# it is Google rate limiting the *deployment*, not the library being slow.
#
# On now because the payoff is the only non-zero value in signals.market and
# signals.virality.trend_growth, and the downside is bounded: the collector
# runs concurrently with DDGS (~6s wall) and returns [] on any error, so even a
# full 7.4s 429 adds ~1.5s rather than 7.4s.
#
# If Render's logs show `google trends error` on every request, this is that
# rate limit and ENABLE_GOOGLE_TRENDS=false costs nothing to set.
ENABLE_GOOGLE_TRENDS = _flag("ENABLE_GOOGLE_TRENDS", True)

# Product Hunt stays off, and the reason is correctness rather than latency --
# measured at 1.0s, it is cheap.
#
# The query is `posts(first: 50)`: the global launch feed, with no topic filter
# anywhere in it. Measured across two unrelated topics it returned the same
# posts and therefore the identical competition_score of 100 and
# avg_votes_per_day of 391.0 for both. A signal that cannot vary with the topic
# is not a signal.
#
# It also displaces real evidence. `_score` awards non-search sources +10, so
# those unrelated launches took 3 of the 30 ranked slots away from sources that
# were actually about the topic, and they are now surfaced to the user as
# citations.
ENABLE_PRODUCT_HUNT = _flag("ENABLE_PRODUCT_HUNT", False)

ENABLE_YOUTUBE = _flag("ENABLE_YOUTUBE", True)

# Per-search result cap handed to DDGS.
DDGS_MAX_RESULTS = _int("DDGS_MAX_RESULTS", 10)

# Hard ceiling on a single collector -- and, inside DDGS, on a single query --
# so one slow source cannot hold the whole response hostage.
#
# Was 12. DDGS has a long tail that never fully drains: measured across four
# topics, collection took exactly the budget at every setting, because some
# query is always still running when it expires.
#
#   budget   collection   ranked   of which web
#      6s        6.01s       30         22
#      8s        8.01s       30         24
#     12s       10.96s       30         26
#
# The ranked evidence count is 30 either way -- MAX_EVIDENCE_ITEMS is the
# binding constraint, not the budget. All the extra seconds buy is a slightly
# different mix, trading YouTube items for search results. 8s keeps as many web
# results as actually reach the prompt (PROMPT_EVIDENCE_ITEMS is 24) and gives
# back ~3s of a ~22s request.
COLLECTOR_TIMEOUT_SECONDS = _int("COLLECTOR_TIMEOUT_SECONDS", 8)

# How many de-duplicated, ranked evidence items survive into signals.
MAX_EVIDENCE_ITEMS = _int("MAX_EVIDENCE_ITEMS", 30 if PORTFOLIO_MODE else 200)

# How many of those are serialised into the LLM prompt, and how much of each
# snippet. The old pipeline sent 10 items with untruncated snippets, three
# times over. This sends more evidence in roughly a third of the tokens.
PROMPT_EVIDENCE_ITEMS = _int("PROMPT_EVIDENCE_ITEMS", 24)
PROMPT_SNIPPET_CHARS = _int("PROMPT_SNIPPET_CHARS", 220)

# The legacy path's three prompts each hardcode evidence[:10].
LEGACY_PROMPT_EVIDENCE_ITEMS = 10


def prompt_evidence_items() -> int:
    """How many ranked items actually reach a prompt, in the current mode."""
    return PROMPT_EVIDENCE_ITEMS if PORTFOLIO_MODE else LEGACY_PROMPT_EVIDENCE_ITEMS


# --------------------------------------------------------------------------
# Evidence in the response
#
# The pipeline used to collect evidence, rank it, feed the top slice to the
# model and then throw all of it away -- the response carried only a count. So
# nothing the model asserted could be traced back to a source, which is a
# strange property for a tool whose whole pitch is that it is evidence-grounded.
#
# The ranked items are already in memory at response time, so returning them
# costs one list comprehension and about 9KB on the wire.
# --------------------------------------------------------------------------

INCLUDE_EVIDENCE = _flag("INCLUDE_EVIDENCE", True)

# Display budget per snippet. Longer than PROMPT_SNIPPET_CHARS because this one
# is read by a person, not paid for by the token.
EVIDENCE_SNIPPET_CHARS = _int("EVIDENCE_SNIPPET_CHARS", 300)


# --------------------------------------------------------------------------
# Search queries
#
# Measured: 12 concurrent searches finish in 5.2s, 5 concurrent searches in
# 5.8s. Wall time is set by the slowest single search, not by the count, so
# trimming the query list buys nothing once the searches run in parallel.
# The list below stays broad on purpose -- it is free.
# --------------------------------------------------------------------------

def search_queries(topic: str) -> list[str]:
    return [
        f"{topic} competitors alternatives",
        f"{topic} reviews complaints problems",
        f"{topic} market size growth forecast",
        f"{topic} funding startup launches",
        f"{topic} pricing",
        f"{topic} trends",
        f"site:reddit.com {topic}",
        f"{topic} industry report CAGR",
    ]


# --------------------------------------------------------------------------
# LLM
# --------------------------------------------------------------------------

# "gemini" or "openrouter".
#
# Gemini is the default because it is the only provider in this codebase with
# a measured track record: it served all 14 cached production runs without a
# single failure. The OpenRouter free tier produced three catastrophic tail
# runs out of those same 14 (64s, 76s, 126s against a 35s median) because
# "openrouter/free" is a router alias that queues behind whichever free model
# it lands on.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# When the primary provider has nothing to give, try the other one before
# giving up.
#
# Gemini's free tier allows 5 requests per minute per model (measured:
# quotaId GenerateRequestsPerMinutePerProjectPerModel-FreeTier, quotaValue 5).
# That is fine for the seeded landing-page suggestions, which never reach a
# provider, and not fine for a visitor typing their own topic -- a couple of
# clicks in a minute and every subsequent request is a 503.
#
# The fallback trades latency for availability. OpenRouter's free models are
# slower and less predictable (measured 64s, 76s and 126s tails against a 34.8s
# median), so this is not a good primary. It is a much better answer than an
# error page on a portfolio link.
ENABLE_LLM_FALLBACK = _flag("ENABLE_LLM_FALLBACK", True)

# Never "openrouter/free" -- that alias is the single largest source of tail
# latency in the measured data.
#
# Free model IDs rotate constantly. The previous default here,
# "google/gemini-2.0-flash-exp:free", was retired and returned
# 404 "No endpoints found" on every call, so this fallback provider was dead
# on arrival. Verified working 2026-07-29; if it 404s, list the current free
# catalogue at https://openrouter.ai/api/v1/models and pick one whose pricing
# is 0, or just leave LLM_PROVIDER=gemini.
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "nvidia/nemotron-3-nano-30b-a3b:free",
)

# thinking_budget=0 disables the reasoning pass on gemini-2.5-flash, which is
# on by default. Synthesis measured 16.9-38.7s (median 25.5s) with thinking
# enabled; this is the single cheapest latency win in the codebase.
GEMINI_THINKING_BUDGET = _int("GEMINI_THINKING_BUDGET", 0)

LLM_TIMEOUT_SECONDS = _int("LLM_TIMEOUT_SECONDS", 75)
LLM_MAX_ATTEMPTS = _int("LLM_MAX_ATTEMPTS", 3)

# How long a provider-suggested retry delay may be before waiting it out stops
# being worth it. A per-minute rate limit answers with a delay of a few
# seconds; an exhausted daily quota answers with no delay at all, and gets no
# retries -- three attempts against a daily quota cost 4.5s of sleeps and
# always failed anyway.
LLM_MAX_RETRY_WAIT_SECONDS = _int("LLM_MAX_RETRY_WAIT_SECONDS", 10)
# Raised from 4096. Every ranked item now carries `detail` and `evidence_ids`
# on top of its name and score, which roughly doubles the reply. At 4096 the
# JSON was being cut mid-object and recovered by the truncation repair path,
# which silently drops whatever came after the cut -- usually synthesis, since
# the model writes it last.
LLM_MAX_OUTPUT_TOKENS = _int("LLM_MAX_OUTPUT_TOKENS", 8192)


# --------------------------------------------------------------------------
# Cache
# --------------------------------------------------------------------------

CACHE_ENABLED = _flag("CACHE_ENABLED", True)
CACHE_TTL_HOURS = _int("CACHE_TTL_HOURS", 24)


def describe() -> str:
    return (
        f"PORTFOLIO_MODE={PORTFOLIO_MODE} "
        f"provider={LLM_PROVIDER} "
        f"model={GEMINI_MODEL if LLM_PROVIDER == 'gemini' else OPENROUTER_MODEL} "
        f"trends={ENABLE_GOOGLE_TRENDS} "
        f"producthunt={ENABLE_PRODUCT_HUNT} "
        f"youtube={ENABLE_YOUTUBE} "
        f"max_evidence={MAX_EVIDENCE_ITEMS}"
    )
