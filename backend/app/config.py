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

# Google Trends is off by default because pytrends 4.9.2 is rate limited by
# Google on essentially every cold call from a cloud IP. Measured: 7.4s to a
# 429, returning zero evidence. It is pure latency with no payload.
ENABLE_GOOGLE_TRENDS = _flag("ENABLE_GOOGLE_TRENDS", not PORTFOLIO_MODE)

# Product Hunt costs two sequential round trips (OAuth token, then GraphQL)
# and returns the global "first 50" feed, which is not filtered by topic. It
# feeds only competitive.launches / market.startup_activity.
ENABLE_PRODUCT_HUNT = _flag("ENABLE_PRODUCT_HUNT", not PORTFOLIO_MODE)

ENABLE_YOUTUBE = _flag("ENABLE_YOUTUBE", True)

# Per-search result cap handed to DDGS.
DDGS_MAX_RESULTS = _int("DDGS_MAX_RESULTS", 10)

# Hard ceiling on a single collector so one slow source cannot hold the whole
# response hostage. Collectors that blow the budget return what they have.
COLLECTOR_TIMEOUT_SECONDS = _int("COLLECTOR_TIMEOUT_SECONDS", 12)

# How many de-duplicated, ranked evidence items survive into signals.
MAX_EVIDENCE_ITEMS = _int("MAX_EVIDENCE_ITEMS", 30 if PORTFOLIO_MODE else 200)

# How many of those are serialised into the LLM prompt, and how much of each
# snippet. The old pipeline sent 10 items with untruncated snippets, three
# times over. This sends more evidence in roughly a third of the tokens.
PROMPT_EVIDENCE_ITEMS = _int("PROMPT_EVIDENCE_ITEMS", 24)
PROMPT_SNIPPET_CHARS = _int("PROMPT_SNIPPET_CHARS", 220)


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

# Never "openrouter/free" -- that alias is the single largest source of tail
# latency in the measured data. Free model IDs rotate frequently, so this is
# an env var: check https://openrouter.ai/models?max_price=0 and set
# OPENROUTER_MODEL if the default 404s.
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "google/gemini-2.0-flash-exp:free",
)

# thinking_budget=0 disables the reasoning pass on gemini-2.5-flash, which is
# on by default. Synthesis measured 16.9-38.7s (median 25.5s) with thinking
# enabled; this is the single cheapest latency win in the codebase.
GEMINI_THINKING_BUDGET = _int("GEMINI_THINKING_BUDGET", 0)

LLM_TIMEOUT_SECONDS = _int("LLM_TIMEOUT_SECONDS", 75)
LLM_MAX_ATTEMPTS = _int("LLM_MAX_ATTEMPTS", 3)
LLM_MAX_OUTPUT_TOKENS = _int("LLM_MAX_OUTPUT_TOKENS", 4096)


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
