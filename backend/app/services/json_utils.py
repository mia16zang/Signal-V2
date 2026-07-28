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
import re

# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------

_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_TRAILING_COMMA = re.compile(r",\s*([}\]])")


def _strip_fences(text: str) -> str:
    match = _FENCE.search(text)
    return match.group(1) if match else text


def _balanced_object(text: str) -> str | None:
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


def parse_json(text: str) -> dict:
    """Best-effort parse. Returns {} when nothing salvageable is found."""
    if not text:
        return {}

    candidates = []

    stripped = text.strip()
    candidates.append(stripped)

    unfenced = _strip_fences(stripped).strip()
    if unfenced != stripped:
        candidates.append(unfenced)

    block = _balanced_object(unfenced)
    if block:
        candidates.append(block)
        candidates.append(_TRAILING_COMMA.sub(r"\1", block))

    for candidate in candidates:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except (ValueError, TypeError):
            continue
        if isinstance(parsed, dict):
            return parsed

    return {}


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


def _object_list(raw, score_key: str, limit: int) -> list:
    """Normalise [{name, <score_key>}] lists."""
    if not isinstance(raw, list):
        return []

    out = []
    for item in raw[:limit]:
        if isinstance(item, str):
            out.append({"name": item.strip(), score_key: 0})
            continue
        if not isinstance(item, dict):
            continue
        name = _text(item.get("name") or item.get("title"))
        if not name:
            continue
        out.append({"name": name, score_key: _clamp_score(item.get(score_key))})
    return out


def _insight_list(raw, limit: int, with_evidence: bool = True) -> list:
    """Normalise [{title, evidence, reason}] lists."""
    if not isinstance(raw, list):
        return []

    out = []
    for item in raw[:limit]:
        if isinstance(item, str):
            title, evidence, reason = item.strip(), "", ""
        elif isinstance(item, dict):
            title = _text(item.get("title") or item.get("name"))
            evidence = _text(item.get("evidence"))
            reason = _text(item.get("reason"))
        else:
            continue

        if not title:
            continue

        if with_evidence:
            out.append({"title": title, "evidence": evidence, "reason": reason})
        else:
            out.append({"title": title, "reason": reason})
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

    return {
        "market_pulse": _clamp_score(raw.get("market_pulse")),
        "opportunity_score": _clamp_score(raw.get("opportunity_score")),
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
    """Split one merged model response into the four contract sections."""
    raw = raw if isinstance(raw, dict) else {}
    return {
        "customer": normalise_customer(raw.get("customer")),
        "market": normalise_market(raw.get("market")),
        "competitive": normalise_competitive(raw.get("competitive")),
        "synthesis": normalise_synthesis(raw.get("synthesis")),
    }
