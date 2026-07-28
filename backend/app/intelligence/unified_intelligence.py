"""The single LLM call.

Replaces four sequential calls (customer -> market -> competitive ->
synthesis) with one request that returns all four sections.

Why this is a real win and not just call-count golf:

  * Three of the four calls were genuinely independent. They received the
    same `evidence[:10]`, serialised three separate times, behind three
    near-identical 4KB preambles. That is three round trips and roughly 3x
    the input tokens to answer three questions about one body of evidence.

  * The fourth (synthesis) did depend on the first three, so it could not be
    parallelised -- it had to wait. Merging removes the dependency instead of
    working around it: the model writes customer/market/competitive first and
    conditions the synthesis on what it just wrote, in one pass.

Measured baseline: 34.8s median for the three extraction calls plus 25.5s
median for synthesis.
"""

import json

from app import config
from app.services.json_utils import normalise_bundle, parse_json

SCHEMA = """{
 "customer": {
  "customer_segments": [{"name": "", "score": 0}],
  "pain_points": [{"name": "", "signal_strength": 0}],
  "desired_outcomes": [{"name": "", "importance": 0}],
  "behavior_patterns": [{"name": "", "confidence": 0}],
  "opportunity_areas": [{"name": "", "score": 0}]
 },
 "market": {
  "market_size": {"estimate": "", "confidence": 0},
  "growth_rate": {"estimate": "", "confidence": 0},
  "market_maturity": {"stage": "", "confidence": 0},
  "future_outlook": {"direction": "", "confidence": 0},
  "key_trends": [{"name": "", "strength": 0}],
  "emerging_trends": [{"name": "", "potential": 0}],
  "market_drivers": [{"name": "", "impact": 0}]
 },
 "competitive": {
  "competitors": [{"name": "", "strength": 0}],
  "competitive_threats": [{"name": "", "severity": 0}],
  "positioning_gaps": [{"name": "", "opportunity": 0}],
  "white_space_opportunities": [{"name": "", "score": 0}],
  "differentiation_opportunities": [{"name": "", "score": 0}]
 },
 "synthesis": {
  "market_pulse": 0,
  "opportunity_score": 0,
  "build_recommendation": {"decision": "", "reason": ""},
  "confidence": 0,
  "confidence_explanation": "",
  "top_reason_to_build": "",
  "biggest_risk": "",
  "best_customer_segment": "",
  "best_moat": "",
  "executive_summary": "",
  "why_now": [{"title": "", "evidence": "", "reason": ""}],
  "key_opportunities": [{"title": "", "evidence": "", "reason": ""}],
  "key_risks": [{"title": "", "evidence": "", "reason": ""}],
  "recommended_customer": "",
  "recommended_positioning": "",
  "potential_moats": [{"title": "", "evidence": "", "reason": ""}],
  "execution_ideas": [{"title": "", "reason": ""}]
 }
}"""


def _format_evidence(evidence) -> str:
    """One line per item. Cheapest useful serialisation.

    The old code embedded a Python list of dicts via f-string repr, which
    spent tokens on braces, quotes and the repeated keys "title"/"snippet"
    for every single item.
    """
    lines = []
    for i, item in enumerate(evidence[:config.PROMPT_EVIDENCE_ITEMS], 1):
        title = (item.get("title") or "").strip()
        snippet = (item.get("snippet") or "").strip()
        snippet = " ".join(snippet.split())[:config.PROMPT_SNIPPET_CHARS]
        source = item.get("source", "")
        lines.append(f"{i}. [{source}] {title} :: {snippet}")
    return "\n".join(lines) or "(no evidence collected)"


def _format_signals(signals) -> str:
    """Only the numbers that carry information.

    Empty containers are dropped rather than serialised as `[]`, which the
    old prompts did unconditionally -- `detected_market_sizes` is always
    empty because nothing in the live pipeline emits `market_report`
    evidence, so every market prompt shipped two empty lists.
    """
    parts = []
    for group, values in (signals or {}).items():
        if not isinstance(values, dict):
            continue
        kept = {
            k: v for k, v in values.items()
            if v not in (0, 0.0, "", None, [], {})
        }
        if kept:
            parts.append(f"{group}: " + json.dumps(kept, separators=(",", ":")))
    return "\n".join(parts) or "(no quantitative signals)"


def build_prompt(topic, evidence, signals, known_competitors=None) -> str:
    known = ", ".join(known_competitors or []) or "none supplied"

    return f"""You are a market analyst, competitive analyst and venture capitalist.
Analyse one topic and return four sections in a single JSON object.

TOPIC: {topic}

QUANTITATIVE SIGNALS:
{_format_signals(signals)}

KNOWN COMPETITORS: {known}

EVIDENCE ({len(evidence[:config.PROMPT_EVIDENCE_ITEMS])} items):
{_format_evidence(evidence)}

TASK

customer     - segments, pain points, desired outcomes, behaviour patterns,
               opportunity areas. 5-8 items each where evidence supports it.
market       - size, growth rate, maturity, outlook, key trends, emerging
               trends, drivers. 5-8 trends where evidence supports it.
competitive  - competitors, threats, positioning gaps, white space,
               differentiation. Max 5 each. Never invent a competitor.
synthesis    - the investment view. Decide whether a startup should enter.
               Max 3 items in each list. Executive summary max 3 sentences,
               reasons under 25 words, evidence fields under 15 words.

Write customer, market and competitive first, then base synthesis only on
what you wrote in them.

RULES

- Ground every conclusion in the evidence above. Do not invent facts,
  companies, statistics or market sizes.
- Weak or missing evidence means low confidence, not a guess.
- Rank strongest items first in every list.
- market_maturity.stage is one of: Emerging, Growth, Mature, Declining.
- build_recommendation.decision is one of: Strong Yes, Yes, Monitor, No.
- Confidence ceiling by supporting sources: 1 source -> 50, 2-3 -> 75,
  4+ -> 90. No evidence -> 0. Never exceed 95.
- In synthesis, never write a number that is not already in the sections
  above. Write "MyFitnessPal", not "MyFitnessPal (95)".
- Every score is a bare JSON integer from 0 to 100. Not "60". Not "high".

Return only this JSON object, with no prose and no code fences:

{SCHEMA}"""


def _service():
    if config.LLM_PROVIDER == "openrouter":
        from app.services.openrouter_service import OpenRouterService
        return OpenRouterService(), config.OPENROUTER_MODEL

    from app.services.gemini_service import GeminiService
    return GeminiService(), config.GEMINI_MODEL


def build_everything(topic, evidence, signals, known_competitors=None):
    """One call. Returns {customer, market, competitive, synthesis}.

    Never raises: a provider failure degrades to an empty-but-valid contract
    so the frontend still renders.
    """
    prompt = build_prompt(topic, evidence, signals, known_competitors)

    service, model = _service()
    print(f"  prompt: {len(prompt)} chars, provider={config.LLM_PROVIDER}, model={model}")

    try:
        raw = service.call(prompt)
    except Exception as e:
        print(f"  LLM CALL FAILED: {type(e).__name__}: {str(e)[:300]}")
        return normalise_bundle({}), False

    parsed = parse_json(raw)

    if not parsed:
        print(f"  JSON UNRECOVERABLE. First 500 chars of response:\n{raw[:500]}")
        return normalise_bundle({}), False

    missing = [k for k in ("customer", "market", "competitive", "synthesis")
               if k not in parsed]
    if missing:
        print(f"  WARNING: model omitted sections {missing}; filled as empty")

    return normalise_bundle(parsed), True
