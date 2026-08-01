"""Definitions that ship with the data.

Everything here used to live in the frontend as hardcoded copy, or nowhere at
all. Keeping it next to the code that computes the numbers means a definition
cannot drift from its metric without someone editing both in the same file.
"""

from app.payload.envelopes import MetricDefinition

# --------------------------------------------------------------------------
# Score scale
#
# The model emits exactly three values. Measured over a full response for
# "Developer tools for edge functions": 75 appeared 19 times, 50 nineteen
# times, 90 nine times -- and nothing else, in any list, ever.
#
# Drawing a continuous progress bar over three possible values is precision
# theatre, so the scale is now declared rather than implied.
# --------------------------------------------------------------------------

SCORE_SCALE = {
    "values": [90, 75, 50],
    "bands": [
        {
            "score": 90,
            "band": "high",
            "label": "Directly supported",
            "meaning": "Stated directly and repeatedly across multiple independent sources.",
        },
        {
            "score": 75,
            "band": "moderate",
            "label": "Clearly indicated",
            "meaning": "Stated clearly but in few sources, or implied consistently across many.",
        },
        {
            "score": 50,
            "band": "low",
            "label": "Inferred",
            "meaning": "Inferred from context; not directly stated in any single source.",
        },
    ],
    "note": (
        "Three bands, not a continuous scale. The model cannot reliably "
        "distinguish a 72 from a 78, so it is not asked to."
    ),
}


# --------------------------------------------------------------------------
# Metric definitions
#
# Audit result for the Customer tab (spec §2): SCORE, SIGNAL STRENGTH and
# IMPORTANCE are the same computation. The prompt asks the model for
# `score`, `signal_strength`, `importance` and `confidence` on four lists
# without ever telling it they mean different things, so no differing
# derivation exists to document -- they are one judgement under four names.
#
# They are therefore collapsed onto `support`. The per-list keys are kept as
# aliases so a frontend holding the old key can still resolve a definition,
# and every alias carries the same `derivation` because that is the truth.
# --------------------------------------------------------------------------

_SHARED_DERIVATION = (
    "The model's own rating of how well the collected evidence backs this item, "
    "quantised to one of three bands. Not a measured quantity."
)
_SHARED_SCALE = "90, 75 or 50 -- reported in three bands, not a continuous scale."

_ALIAS_DEFINITIONS = {
    "support": ("Support", "How consistently this item appeared across the collected sources."),
    "score": ("Score", "How consistently this item appeared across the collected sources."),
    "signal_strength": ("Signal strength", "How often and how emphatically this was raised in the source material."),
    "importance": ("Importance", "How central this was to the discussions where it appeared."),
    "confidence": ("Confidence", "How consistently this pattern appeared across the collected sources."),
    "strength": ("Strength", "How established this is across the collected sources."),
    "potential": ("Potential", "How much room this has to grow, judged from the collected sources."),
    "impact": ("Impact", "How strongly this shapes the market, judged from the collected sources."),
    "severity": ("Severity", "How directly this threat overlaps with the proposed product."),
    "opportunity": ("Opportunity", "How much unmet demand this gap represents in the collected sources."),
}

# Which alias each list historically used, so `report` can tell the frontend
# what the old column header on that list was called.
LIST_METRIC_KEYS = {
    "customer_segments": "score",
    "pain_points": "signal_strength",
    "desired_outcomes": "importance",
    "behavior_patterns": "confidence",
    "opportunity_areas": "score",
    "key_trends": "strength",
    "emerging_trends": "potential",
    "market_drivers": "impact",
    "competitors": "strength",
    "competitive_threats": "severity",
    "positioning_gaps": "opportunity",
    "white_space_opportunities": "score",
    "differentiation_opportunities": "score",
    "why_now": "support",
    "key_opportunities": "support",
    "key_risks": "support",
    "potential_moats": "support",
    "execution_ideas": "support",
}

LIST_LABELS = {
    "customer_segments": "Customer segments",
    "pain_points": "Pain points",
    "desired_outcomes": "Desired outcomes",
    "behavior_patterns": "Behaviour patterns",
    "opportunity_areas": "Opportunity areas",
    "key_trends": "Key trends",
    "emerging_trends": "Emerging trends",
    "market_drivers": "Market drivers",
    "competitors": "Competitors",
    "competitive_threats": "Competitive threats",
    "positioning_gaps": "Positioning gaps",
    "white_space_opportunities": "White space",
    "differentiation_opportunities": "Differentiation",
    "why_now": "Why now",
    "key_opportunities": "Key opportunities",
    "key_risks": "Key risks",
    "potential_moats": "Potential moats",
    "execution_ideas": "Execution ideas",
}


def metric_definitions() -> list[MetricDefinition]:
    """Every metric key the payload uses, with a self-contained definition.

    Constructing through the model runs the validator, so a definition that
    restates its own label fails here at import time rather than shipping.
    """
    out = [
        MetricDefinition(
            key=key,
            label=label,
            definition=definition,
            derivation=_SHARED_DERIVATION,
            scale=_SHARED_SCALE,
        )
        for key, (label, definition) in _ALIAS_DEFINITIONS.items()
    ]

    for spec in SIGNAL_SPECS.values():
        out.append(
            MetricDefinition(
                key=spec["key"],
                label=spec["label"],
                definition=spec["definition"],
                derivation=spec["derivation"],
                scale=spec["scale"],
            )
        )

    return out


# --------------------------------------------------------------------------
# Sources
#
# `ddgs` is a Python package name. It has no business appearing in a filter
# pill on a briefing page.
# --------------------------------------------------------------------------

SOURCE_LABELS = {
    "ddgs": "Web search",
    "youtube": "YouTube",
    "google_trends": "Google Trends",
    "producthunt": "Product Hunt",
    "market_reports": "Market reports",
    "unknown": "Unknown source",
}


def source_label(key: str) -> str:
    return SOURCE_LABELS.get(key, key.replace("_", " ").title())


# --------------------------------------------------------------------------
# Raw signals
#
# `feeds` names the collector a signal is derived from. It is what makes
# "collected: false" computable: if that collector put nothing into the ranked
# evidence, the signal was never measured, and a 0 would be a lie.
#
# `feeds: None` means the signal is derived from the evidence text itself, so
# it is measured whenever any evidence exists.
# --------------------------------------------------------------------------

SIGNAL_SPECS = {
    ("customer", "discussion_volume"): {
        "key": "discussion_volume",
        "label": "Discussions",
        "definition": "Ranked sources matching this topic across every collector.",
        "derivation": "Count of items in the ranked evidence list.",
        "scale": "Whole number of sources.",
        "unit": None,
        "feeds": None,
    },
    ("customer", "comment_volume"): {
        "key": "comment_volume",
        "label": "Comments",
        "definition": "Total viewer replies across the collected videos.",
        "derivation": "Sum of the YouTube comment count on every collected video.",
        "scale": "Whole number.",
        "unit": None,
        "feeds": "youtube",
    },
    ("market", "growth_score"): {
        "key": "growth_score",
        "label": "Growth score",
        "definition": "Movement in search interest for this topic over the sampled window.",
        "derivation": "Google Trends growth rate for the topic term.",
        "scale": "Percentage change.",
        "unit": "%",
        "feeds": "google_trends",
    },
    ("market", "startup_activity"): {
        "key": "startup_activity",
        "label": "Startup activity",
        "definition": "New products shipped into this space recently.",
        "derivation": "Count of Product Hunt launches in the collected evidence.",
        "scale": "Whole number of launches.",
        "unit": None,
        "feeds": "producthunt",
    },
    ("competitive", "launches"): {
        "key": "launches",
        "label": "Launches",
        "definition": "Recent product releases observed in this space.",
        "derivation": "Count of Product Hunt items in the collected evidence.",
        "scale": "Whole number.",
        "unit": None,
        "feeds": "producthunt",
    },
    ("competitive", "avg_votes_per_day"): {
        "key": "avg_votes_per_day",
        "label": "Avg votes / day",
        "definition": "Mean daily upvotes across those releases.",
        "derivation": "Product Hunt votes divided by days since launch, averaged.",
        "scale": "Votes per day.",
        "unit": None,
        "feeds": "producthunt",
    },
    ("competitive", "competition_score"): {
        "key": "competition_score",
        "label": "Competition score",
        "definition": "How crowded the field looks, from launch count and traction.",
        "derivation": "min(100, launches x 2 + mean votes per day).",
        "scale": "0-100.",
        "unit": None,
        "feeds": "producthunt",
    },
    ("virality", "momentum"): {
        "key": "momentum",
        "label": "Momentum",
        "definition": "How fast attention is moving on this topic.",
        "derivation": "Weighted blend of search growth, video engagement and daily views.",
        "scale": "0-100.",
        "unit": None,
        "feeds": "google_trends+youtube",
    },
    ("virality", "trend_growth"): {
        "key": "trend_growth",
        "label": "Trend growth",
        "definition": "Change in search interest over the sampled window.",
        "derivation": "Google Trends growth rate for the topic term.",
        "scale": "Percentage change.",
        "unit": "%",
        "feeds": "google_trends",
    },
    ("virality", "avg_views_per_day"): {
        "key": "avg_views_per_day",
        "label": "Avg views / day",
        "definition": "Mean daily plays across the collected videos.",
        "derivation": "Lifetime views divided by days since publication, averaged.",
        "scale": "Views per day.",
        "unit": None,
        "feeds": "youtube",
    },
    ("virality", "avg_engagement_rate"): {
        "key": "avg_engagement_rate",
        "label": "Engagement rate",
        "definition": "Likes and comments per 100 plays on the collected videos.",
        "derivation": "(likes + comments) / views x 100, averaged across videos.",
        "scale": "Percentage.",
        "unit": "%",
        "feeds": "youtube",
    },
    ("market_size", "market_reports"): {
        "key": "market_reports",
        "label": "Market reports",
        "definition": "Collected sources that read as dedicated industry research.",
        "derivation": "Sources whose text contains 'market size', 'market forecast' or 'industry report'.",
        "scale": "Whole number of sources.",
        "unit": None,
        "feeds": None,
    },
}

# Mention counts under market_opportunity share one definition -- individually
# they are too granular to caption, and the UI renders them as one card.
MENTION_KEYS = (
    "market_size_mentions",
    "growth_mentions",
    "forecast_mentions",
    "cagr_mentions",
    "billion_mentions",
    "million_mentions",
)

MENTION_GROUP_DEFINITION = (
    "How often each kind of sizing language appeared in the collected sources. "
    "A property of the writing, not evidence of the market's actual size."
)

# Fields kept in the payload only so the deployed frontend keeps rendering.
# Nothing new should read them, and a cleanup pass removes them once session 3
# has moved across.
DEPRECATED_FIELDS = [
    {
        "path": "signals.market_opportunity.opportunity_score",
        "replacement": "report.signals.market_opportunity.sizing_language_density",
        "reason": (
            "A weighted keyword sum clamped at 100. The weights were set when "
            "the extractor was gated to dedicated market-report sources; it now "
            "scans all 30 ranked sources, so the sum clears the clamp on "
            "ordinary inputs and the value saturates. Counts replace it."
        ),
    },
    {
        "path": "synthesis.opportunity_score",
        "replacement": "report.verdict.decision",
        "reason": (
            "A 0-100 composite the model writes with no stated formula. The "
            "verdict is the decision and its reason; a number cannot carry "
            "that and invites the interface to render it as a hero gauge."
        ),
    },
]
