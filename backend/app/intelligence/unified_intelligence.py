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
import logging
import os

from app import config
from app.services.json_utils import normalise_bundle, parse_json_verbose

log = logging.getLogger("signal.intelligence")

# Every ranked item now carries three things it did not before: a `detail` for
# the drawer, `evidence_ids` pointing at the sources behind it, and a score
# restricted to three values. `name` is capped at 10 words because it is a list
# row -- the long strings the model used to return were being cut off by CSS,
# which threw away the only part of the row that carried meaning.
def _row(score_key: str) -> str:
    return (
        f'{{"name": "", "{score_key}": 90, "detail": "", "evidence_ids": ["e1"]}}'
    )


_INSIGHT = ('{"title": "", "score": 90, "evidence": "", "reason": "", '
            '"evidence_ids": ["e1"]}')

SCHEMA = f"""{{
 "customer": {{
  "customer_segments": [{_row("score")}],
  "pain_points": [{_row("signal_strength")}],
  "desired_outcomes": [{_row("importance")}],
  "behavior_patterns": [{_row("confidence")}],
  "opportunity_areas": [{_row("score")}]
 }},
 "market_sizing": {{
  "claims": [{{"evidence_id": "e1", "figure_text": "", "year": 2030, "scope": ""}}]
 }},
 "market": {{
  "market_size": {{"estimate": "", "confidence": 0}},
  "growth_rate": {{"estimate": "", "confidence": 0}},
  "market_maturity": {{"stage": "", "confidence": 0}},
  "future_outlook": {{"direction": "", "confidence": 0}},
  "key_trends": [{_row("strength")}],
  "emerging_trends": [{_row("potential")}],
  "market_drivers": [{_row("impact")}]
 }},
 "competitive": {{
  "competitors": [{_row("strength")}],
  "competitive_threats": [{_row("severity")}],
  "positioning_gaps": [{_row("opportunity")}],
  "white_space_opportunities": [{_row("score")}],
  "differentiation_opportunities": [{_row("score")}]
 }},
 "synthesis": {{
  "build_recommendation": {{"decision": "", "reason": ""}},
  "confidence": 0,
  "confidence_explanation": "",
  "top_reason_to_build": "",
  "biggest_risk": "",
  "best_customer_segment": "",
  "best_moat": "",
  "executive_summary": "",
  "why_now": [{_INSIGHT}],
  "key_opportunities": [{_INSIGHT}],
  "key_risks": [{_INSIGHT}],
  "recommended_customer": "",
  "recommended_positioning": "",
  "potential_moats": [{_INSIGHT}],
  "execution_ideas": [{{"title": "", "score": 90, "reason": "", "evidence_ids": ["e1"]}}]
 }}
}}"""


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
        # `eN` is the id the model cites back in `evidence_ids`. It matches the
        # id assigned in app.payload.normalise.assign_evidence_ids, which keys
        # off the same rank, so a cited id resolves to the same source the
        # model was shown.
        lines.append(f"e{i}. [{source}] {title} :: {snippet}")
    return "\n".join(lines) or "(no evidence collected)"


def _format_signals(signals) -> str:
    """Only the numbers that carry information.

    Empty containers are dropped rather than serialised as `[]`, which the old
    prompts did unconditionally. That mattered most for `detected_market_sizes`
    and `detected_growth_rates`, which were empty on every single request
    because of the dead source filter in market_opportunity_signals. Now that
    they populate, they reach the prompt -- roughly 100 characters of real
    figures the model can ground `market.market_size` against, rather than two
    empty brackets.
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
               Max 3 items in each list. Executive summary max 3 sentences.

Write customer, market and competitive first, then base synthesis only on
what you wrote in them.

RULES

Evidence
- Ground every conclusion in the evidence above. Do not invent facts,
  companies, statistics or market sizes.
- Every list item must cite the evidence behind it in `evidence_ids`, using
  the `eN` ids exactly as they appear above. Cite only ids you actually used.
  An item you cannot cite is an item you should not return.

Scoring — exactly three values
- Every score is one of 90, 75 or 50. No other value is valid. Not 80, not 65,
  not "high", not "60".
    90 - stated directly and repeatedly across multiple independent sources
    75 - stated clearly but in few sources, or implied consistently across many
    50 - inferred from context; not directly stated in any single source
- `confidence` on the four market estimates is a 0-100 integer, not banded.
  Ceiling by supporting sources: 1 source -> 50, 2-3 -> 75, 4+ -> 90.
  Never exceed 95.

Length
- `name` and `title`: at most 10 words, no trailing punctuation. These render
  as one line in a list. Put the explanation in `detail`, not here.
- `detail`: one or two complete sentences.
- `reason`: under 25 words. `evidence`: under 15 words.

Do not repeat yourself
- recommended_customer, best_customer_segment, recommended_positioning and
  best_moat must each say something the others do not.
  recommended_customer is who to sell to first -- the narrow beachhead.
  best_customer_segment is the broader group that shares the same pain.
  If you cannot make one materially different from the others, return null
  for it rather than restating a neighbour.

market_sizing — extraction only, no judgement
- List every source above that states the size of a *market*, and only those.
- A funding round, a company's revenue, a valuation, a customer count or a
  single deal is not a market size. Leave those out entirely — mixing them in
  produces a range spanning a startup's seed round and a global market, which
  is not a disagreement about one quantity.
- `figure_text` must be copied verbatim from the source, character for
  character, exactly as it appears. It is checked against the source text and
  the claim is discarded if it does not match, so do not tidy, reformat,
  convert or round it.
- `evidence_id` is the `eN` of the source the figure came from.
- `scope` is what the figure measures, in the source's own framing
  (for example "Edge AI software, global"). `year` is the year the figure
  targets, or null.
- If no source states a market size, return `"claims": []`. That is a normal
  and common outcome. Do not estimate one, do not infer one from adjacent
  markets, and do not carry a figure over from `market.market_size`.

Numbers
- Return null for any quantitative estimate the evidence does not directly
  support. A plausible invented figure is worse than no figure.
- In synthesis, never write a number that is not already in the sections
  above. Write "MyFitnessPal", not "MyFitnessPal (95)".
- market_maturity.stage is one of: Emerging, Growth, Mature, Declining.
- build_recommendation.decision is one of: Strong Yes, Yes, Monitor, No.
- Rank strongest items first in every list.

Return only this JSON object, with no prose and no code fences:

{SCHEMA}"""


def _service():
    if config.LLM_PROVIDER == "openrouter":
        from app.services.openrouter_service import OpenRouterService
        return OpenRouterService(), config.OPENROUTER_MODEL

    from app.services.gemini_service import GeminiService
    return GeminiService(), config.GEMINI_MODEL


def _fallback_service():
    """The other provider, used only when the first returns nothing.

    Deliberately a separate function rather than a parameter on `_service`:
    the verifier swaps `_service` for a stub, and a signature change there
    would break every test that does so.
    """
    if not config.ENABLE_LLM_FALLBACK:
        return None, None

    # Gemini is the fallback when OpenRouter is primary, and vice versa.
    if config.LLM_PROVIDER == "openrouter":
        if not os.getenv("GEMINI_API_KEY"):
            return None, None
        from app.services.gemini_service import GeminiService
        return GeminiService(), config.GEMINI_MODEL

    if not os.getenv("OPENROUTER_API_KEY"):
        return None, None
    from app.services.openrouter_service import OpenRouterService
    return OpenRouterService(), config.OPENROUTER_MODEL


VALID_SCORES = (90, 75, 50)


def _walk_items(parsed):
    """Every ranked item in the reply, with a path for the log."""
    for section in ("customer", "market", "competitive", "synthesis"):
        block = parsed.get(section)
        if not isinstance(block, dict):
            continue
        for key, value in block.items():
            if not isinstance(value, list):
                continue
            for index, item in enumerate(value, 1):
                if isinstance(item, dict):
                    yield f"{section}.{key}[{index}]", key, item


def _violations(parsed, valid_ids):
    """Compliance failures worth one retry.

    Deliberately narrow. Only the two rules the payload cannot repair on its
    own are checked: a score off the declared scale would have to be snapped
    to the nearest band, and a missing citation cannot be reconstructed
    server-side without inventing the link.
    """
    off_scale, uncited = [], []

    for path, key, item in _walk_items(parsed):
        score = item.get("score")
        for candidate in ("score", "signal_strength", "importance", "confidence",
                          "strength", "potential", "impact", "severity",
                          "opportunity"):
            if candidate in item:
                score = item[candidate]
                break
        if isinstance(score, (int, float)) and int(score) not in VALID_SCORES:
            off_scale.append(f"{path}={score}")

        cited = [i for i in (item.get("evidence_ids") or []) if i in valid_ids]
        if not cited:
            uncited.append(path)

    return off_scale, uncited


def _call_once(service, prompt, topic):
    try:
        raw = service.call(prompt)
    except Exception as e:
        log.warning("LLM call failed | query=%r %s: %s",
                    topic, type(e).__name__, str(e)[:300])
        print(f"  LLM CALL FAILED: {type(e).__name__}: {str(e)[:300]}")
        return None, {
            "strategy": "call_failed",
            # The classified phrase, not the provider's raw body. The full
            # error is already in the WARNING above; repeating it here would
            # carry it into `degraded_reason` and out through the HTTP
            # response, where it is noise at best and internals at worst.
            "detail": getattr(e, "reason", None) or f"{type(e).__name__}",
            "retry_after": getattr(e, "retry_after", None),
        }

    parsed, report = parse_json_verbose(raw, topic)
    return (parsed or None), report


def build_everything(topic, evidence, signals, known_competitors=None):
    """One call, plus at most one corrective retry.

    Never raises: a provider failure degrades to an empty-but-valid contract
    so the frontend still renders.
    """
    prompt = build_prompt(topic, evidence, signals, known_competitors)
    valid_ids = {f"e{i}" for i in range(1, len(evidence[:config.PROMPT_EVIDENCE_ITEMS]) + 1)}

    service, model = _service()
    print(f"  prompt: {len(prompt)} chars, provider={config.LLM_PROVIDER}, model={model}")

    parsed, parse_report = _call_once(service, prompt, topic)
    degraded: list[str] = []

    # "call_failed" is not a repair strategy -- no reply arrived to repair. It
    # is reported by the fallback block below, or as the failure reason if
    # there is no fallback, so describing it here produced the phrase
    # "model reply needed call_failed".
    if parse_report.get("strategy") not in ("direct", "call_failed", None):
        degraded.append(
            f"model reply needed {parse_report['strategy']}"
            + (f", {parse_report['chars_lost']} chars discarded"
               if parse_report.get("chars_lost") else "")
        )

    if parsed:
        off_scale, uncited = _violations(parsed, valid_ids)
        if off_scale or uncited:
            print(f"  compliance: {len(off_scale)} off-scale scores, "
                  f"{len(uncited)} uncited items -- retrying once")
            if off_scale[:3]:
                print(f"    e.g. {', '.join(off_scale[:3])}")

            retry, retry_report = _call_once(service, topic=topic, prompt=prompt + f"""

Your previous reply broke two rules. Return the whole JSON object again, fixed.

- {len(off_scale)} scores were not 90, 75 or 50. Every score must be exactly
  one of those three integers.
- {len(uncited)} items had a missing or unrecognised `evidence_ids`. Every item
  needs at least one id from the list above, written exactly as `e1`, `e2`.""")

            if retry:
                still_off, still_uncited = _violations(retry, valid_ids)
                # Only keep the retry if it is actually better. A retry that
                # regressed is worse than the original reply.
                if len(still_off) + len(still_uncited) < len(off_scale) + len(uncited):
                    parsed = retry
                    off_scale, uncited = still_off, still_uncited
                    parse_report = retry_report
                print(f"  after retry: {len(off_scale)} off-scale, {len(uncited)} uncited")

            if uncited:
                degraded.append(f"{len(uncited)} insights could not cite a source")
            if off_scale:
                degraded.append(
                    f"{len(off_scale)} scores were off the declared scale and "
                    f"were snapped to the nearest band"
                )

    # The primary had nothing to give. Before returning an error page, try the
    # other provider -- a slower briefing from a second model beats a 503 on a
    # link someone is looking at right now.
    provider_used = config.LLM_PROVIDER
    if not parsed:
        fallback, fallback_model = _fallback_service()
        if fallback is not None:
            print(f"  primary unavailable ({parse_report.get('detail')}); "
                  f"falling back to {fallback_model}")
            log.warning("falling back to secondary provider | query=%r reason=%s",
                        topic, parse_report.get("detail"))

            parsed, fallback_report = _call_once(fallback, prompt, topic)
            if parsed:
                provider_used = "openrouter" if config.LLM_PROVIDER != "openrouter" else "gemini"
                # Said out loud in the payload, not hidden. The briefing was
                # written by a different model than the one the timings and the
                # rest of the response describe.
                degraded.append(
                    f"the usual model was unavailable; this briefing was written "
                    f"by the fallback model ({fallback_model})"
                )
                parse_report = fallback_report
            else:
                parse_report.setdefault("fallback_detail",
                                        fallback_report.get("detail"))

    if not parsed:
        log.warning("no usable model output | query=%r strategy=%s",
                    topic, parse_report.get("strategy"))
        # Say which of the two it was. Printing "JSON UNRECOVERABLE" for a call
        # that never returned is what made a 429 look like a parsing problem
        # for the first half of this session.
        if parse_report.get("strategy") == "call_failed":
            print(f"  NO MODEL OUTPUT: {parse_report.get('detail')}")
        else:
            print("  JSON UNRECOVERABLE: a reply arrived but could not be parsed")

        reason = (f"no usable model output ({parse_report.get('detail')})"
                  if parse_report.get("strategy") == "call_failed"
                  else "the model reply could not be parsed")
        return (normalise_bundle({}), False, [reason],
                parse_report.get("retry_after"), provider_used)

    missing = [k for k in ("customer", "market", "competitive", "synthesis")
               if k not in parsed]
    if missing:
        # Not cosmetic: normalise_bundle fills these with empty structures, so
        # without this the response is indistinguishable from a topic that
        # genuinely had nothing to say.
        log.warning("model omitted sections %s | query=%r", missing, topic)
        print(f"  WARNING: model omitted sections {missing}; filled as empty")
        degraded.append(f"model omitted section(s): {', '.join(missing)}")

    return normalise_bundle(parsed), True, degraded, None, provider_used
