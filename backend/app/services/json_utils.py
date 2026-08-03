"""Robust JSON extraction and contract enforcement.

Two jobs:

1. `parse_json` turns whatever the model actually returned into a dict. It
   keeps every recovery strategy the old code had (direct parse, then a
   regex-ish extraction) and adds fence stripping, balanced-brace scanning,
   trailing-comma repair and truncation repair.

2. `normalise_result` guarantees the response shape the frontend already
   consumes. The old pipeline handed the model's raw output straight to the
   client, so a single omitted key could surface as a crash in the UI. Every
   key below is present in every response now, empty rather than missing.
"""

from __future__ import annotations

import json
import logging
import re

log = logging.getLogger("signal.parse")

# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------

_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_TRAILING_COMMA = re.compile(r",\s*([}\]])")


def _strip_fences(text: str) -> str:
    match = _FENCE.search(text)
    return match.group(1) if match else text


def _balanced_object(text: str, report: dict | None = None) -> str | None:
    """Return the first complete top-level {...} block.

    The old code used `re.search(r"\\{.*\\}", text, re.DOTALL)`, which is
    greedy and grabs everything between the first and last brace in the whole
    response -- including any prose the model appended after the JSON. This
    walks the string instead and respects strings and escapes.
    """
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False

    for i in range(start, len(text)):
        ch = text[i]

        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]

    # Unbalanced: the model was cut off mid-object. Close what is open.
    #
    # This is the path that was silently discarding content. Whatever the model
    # had not finished writing is gone, and because the model writes synthesis
    # last, what is gone is usually the verdict.
    if report is not None:
        report["truncated"] = True
        report["depth_at_cut"] = depth
    return _repair_truncated(text[start:], in_string)


def _repair_truncated(fragment: str, in_string: bool) -> str:
    """Close an object that ran out of output tokens mid-write."""
    if in_string:
        fragment += '"'

    # Drop a dangling `"key":` or trailing comma before closing.
    fragment = re.sub(r",\s*\"[^\"]*\"\s*:\s*$", "", fragment)
    fragment = re.sub(r",\s*$", "", fragment)

    depth = 0
    in_str = False
    escaped = False
    stack = []

    for ch in fragment:
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch in "{[":
            stack.append(ch)
        elif ch in "}]" and stack:
            stack.pop()

    for opener in reversed(stack):
        fragment += "}" if opener == "{" else "]"

    return fragment


def parse_json_verbose(text: str, query: str = "") -> tuple[dict, dict]:
    """Parse, and say which recovery strategy was needed to do it.

    The recovery ladder was silent: a reply that needed truncation repair and
    a reply that parsed cleanly were indistinguishable to every caller. That
    is how a briefing missing its synthesis section could be served as if it
    were complete.
    """
    report = {"strategy": None, "truncated": False, "chars_in": len(text or ""),
              "chars_parsed": 0, "chars_lost": 0}

    if not text:
        report["strategy"] = "failed"
        log.warning("empty model reply | query=%r", query)
        return {}, report

    stripped = text.strip()
    candidates = [("direct", stripped)]

    unfenced = _strip_fences(stripped).strip()
    if unfenced != stripped:
        candidates.append(("fence_stripped", unfenced))

    block = _balanced_object(unfenced, report)
    if block:
        candidates.append(
            ("truncation_repaired" if report["truncated"] else "balanced_scan", block)
        )
        candidates.append(
            ("trailing_comma_repaired", _TRAILING_COMMA.sub(r"\1", block))
        )

    for strategy, candidate in candidates:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except (ValueError, TypeError):
            continue
        if not isinstance(parsed, dict):
            continue

        report["strategy"] = strategy
        report["chars_parsed"] = len(candidate)
        report["chars_lost"] = max(0, len(stripped) - len(candidate))

        if strategy != "direct":
            log.warning(
                "model reply needed repair | query=%r strategy=%s "
                "chars_in=%d chars_parsed=%d chars_lost=%d",
                query, strategy, report["chars_in"],
                report["chars_parsed"], report["chars_lost"],
            )
        return parsed, report

    report["strategy"] = "failed"
    log.warning(
        "model reply unparseable | query=%r chars_in=%d first_200=%r",
        query, report["chars_in"], text[:200],
    )
    return {}, report


def parse_json(text: str) -> dict:
    """Best-effort parse. Returns {} when nothing salvageable is found."""
    return parse_json_verbose(text)[0]


# --------------------------------------------------------------------------
# Contract enforcement
# --------------------------------------------------------------------------

def _clamp_score(value, default: int = 0) -> int:
    """Coerce whatever the model produced into an int in [0, 100].

    Models return "60", 60.0, "high" and 160 interchangeably despite the
    prompt. The frontend renders these as bar widths, so a string or an
    out-of-range value is a visual bug.
    """
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return max(0, min(100, int(value)))
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value)
        if match:
            return max(0, min(100, int(float(match.group()))))
    return default


def _text(value) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value)


MAX_LABEL_WORDS = 10


def _label(value, key: str) -> str:
    """Cap a list label at MAX_LABEL_WORDS, loudly.

    The frontend was clamping these with CSS, which meant the row rendered
    `Established platforms offering comprehensive e...` -- the label is the
    entire payload of the row, so cutting it there destroys the information.
    Truncating here instead makes the limit visible in the response and in the
    log, rather than a rendering accident.
    """
    words = (value or "").split()
    if len(words) <= MAX_LABEL_WORDS:
        return value
    print(f"  label over {MAX_LABEL_WORDS} words, truncated ({key}): {value!r}")
    return " ".join(words[:MAX_LABEL_WORDS]).rstrip(",;:") + "…"


def _evidence_ids(raw) -> list:
    """Keep only well-formed `eN` ids. Shape is checked; existence is not.

    `build_insight_list` drops ids that do not match a collected item, because
    only it knows the evidence list.
    """
    if not isinstance(raw, list):
        return []
    return [i for i in (str(x).strip() for x in raw) if re.fullmatch(r"e\d+", i)]


def _object_list(raw, score_key: str, limit: int) -> list:
    """Normalise [{name, <score_key>}] lists.

    `detail` and `evidence_ids` are additive: absent on older cached responses
    and on any model reply that ignores them, so both default empty rather than
    dropping the item.
    """
    if not isinstance(raw, list):
        return []

    out = []
    for item in raw[:limit]:
        if isinstance(item, str):
            out.append({"name": item.strip(), score_key: 0,
                        "detail": "", "evidence_ids": []})
            continue
        if not isinstance(item, dict):
            continue
        name = _text(item.get("name") or item.get("title"))
        if not name:
            continue
        out.append({
            "name": _label(name, score_key),
            score_key: _clamp_score(item.get(score_key)),
            "detail": _text(item.get("detail")),
            "evidence_ids": _evidence_ids(item.get("evidence_ids")),
        })
    return out


def _insight_list(raw, limit: int, with_evidence: bool = True) -> list:
    """Normalise [{title, evidence, reason}] lists."""
    if not isinstance(raw, list):
        return []

    out = []
    for item in raw[:limit]:
        if isinstance(item, str):
            title, evidence, reason = item.strip(), "", ""
            score, ids, detail = 0, [], ""
        elif isinstance(item, dict):
            title = _text(item.get("title") or item.get("name"))
            evidence = _text(item.get("evidence"))
            reason = _text(item.get("reason"))
            detail = _text(item.get("detail")) or reason
            score = _clamp_score(item.get("score"))
            ids = _evidence_ids(item.get("evidence_ids"))
        else:
            continue

        if not title:
            continue

        row = {"title": _label(title, "title"), "reason": reason,
               "detail": detail, "score": score, "evidence_ids": ids}
        if with_evidence:
            row["evidence"] = evidence
        out.append(row)
    return out


def _estimate(raw, value_key: str) -> dict:
    if not isinstance(raw, dict):
        return {value_key: "", "confidence": 0}
    return {
        value_key: _text(raw.get(value_key)),
        "confidence": _clamp_score(raw.get("confidence")),
    }


def normalise_customer(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    return {
        "customer_segments": _object_list(raw.get("customer_segments"), "score", 10),
        "pain_points": _object_list(raw.get("pain_points"), "signal_strength", 10),
        "desired_outcomes": _object_list(raw.get("desired_outcomes"), "importance", 10),
        "behavior_patterns": _object_list(raw.get("behavior_patterns"), "confidence", 10),
        "opportunity_areas": _object_list(raw.get("opportunity_areas"), "score", 10),
    }


def normalise_market(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    maturity = raw.get("market_maturity")
    outlook = raw.get("future_outlook")
    return {
        "market_size": _estimate(raw.get("market_size"), "estimate"),
        "growth_rate": _estimate(raw.get("growth_rate"), "estimate"),
        "market_maturity": {
            "stage": _text(maturity.get("stage")) if isinstance(maturity, dict) else "",
            "confidence": _clamp_score(
                maturity.get("confidence") if isinstance(maturity, dict) else None
            ),
        },
        "future_outlook": {
            "direction": _text(outlook.get("direction")) if isinstance(outlook, dict) else "",
            "confidence": _clamp_score(
                outlook.get("confidence") if isinstance(outlook, dict) else None
            ),
        },
        "key_trends": _object_list(raw.get("key_trends"), "strength", 10),
        "emerging_trends": _object_list(raw.get("emerging_trends"), "potential", 10),
        "market_drivers": _object_list(raw.get("market_drivers"), "impact", 10),
    }


def normalise_competitive(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    return {
        "competitors": _object_list(raw.get("competitors"), "strength", 5),
        "competitive_threats": _object_list(raw.get("competitive_threats"), "severity", 5),
        "positioning_gaps": _object_list(raw.get("positioning_gaps"), "opportunity", 5),
        "white_space_opportunities": _object_list(
            raw.get("white_space_opportunities"), "score", 5
        ),
        "differentiation_opportunities": _object_list(
            raw.get("differentiation_opportunities"), "score", 5
        ),
    }


_DECISIONS = ("Strong Yes", "Yes", "Monitor", "No")


def normalise_synthesis(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}

    recommendation = raw.get("build_recommendation")
    if not isinstance(recommendation, dict):
        recommendation = {}

    decision = _text(recommendation.get("decision"))
    match = next(
        (d for d in _DECISIONS if d.lower() == decision.lower()),
        None,
    )

    # `market_pulse` and `opportunity_score` are both gone as of session 4.
    #
    # opportunity_score was a weighted keyword sum clamped at 100, which
    # saturated on ordinary inputs once the extractor stopped being gated to
    # dedicated market-report sources. market_pulse had no derivation at all
    # and moved 92 points across five identical runs.
    #
    # Both were removed rather than repaired: neither had a scale anyone could
    # state, and both were driving hero-sized numbers in the interface.
    # `report.signals.market_opportunity.sizing_language_density` carries the
    # underlying counts instead.
    return {
        "build_recommendation": {
            "decision": match or (decision if decision else "Monitor"),
            "reason": _text(recommendation.get("reason")),
        },
        "confidence": min(95, _clamp_score(raw.get("confidence"))),
        "confidence_explanation": _text(raw.get("confidence_explanation")),
        "top_reason_to_build": _text(raw.get("top_reason_to_build")),
        "biggest_risk": _text(raw.get("biggest_risk")),
        "best_customer_segment": _text(raw.get("best_customer_segment")),
        "best_moat": _text(raw.get("best_moat")),
        "executive_summary": _text(raw.get("executive_summary")),
        "why_now": _insight_list(raw.get("why_now"), 3),
        "key_opportunities": _insight_list(raw.get("key_opportunities"), 3),
        "key_risks": _insight_list(raw.get("key_risks"), 3),
        "recommended_customer": _text(raw.get("recommended_customer")),
        "recommended_positioning": _text(raw.get("recommended_positioning")),
        "potential_moats": _insight_list(raw.get("potential_moats"), 3),
        "execution_ideas": _insight_list(
            raw.get("execution_ideas"), 3, with_evidence=False
        ),
    }


def normalise_bundle(raw: dict) -> dict:
    """Split one merged model response into the contract sections."""
    raw = raw if isinstance(raw, dict) else {}

    sizing = raw.get("market_sizing")
    claims = sizing.get("claims") if isinstance(sizing, dict) else None

    return {
        "customer": normalise_customer(raw.get("customer")),
        "market": normalise_market(raw.get("market")),
        "competitive": normalise_competitive(raw.get("competitive")),
        "synthesis": normalise_synthesis(raw.get("synthesis")),
        # Carried through unvalidated on purpose. Every claim is verified
        # against the source it cites in app.payload.sizing, which is the only
        # place that can see the evidence text, so shaping it here would just
        # be a second, weaker check.
        "market_sizing": {"claims": claims if isinstance(claims, list) else []},
    }
