from app.services.openrouter_service import (
    OpenRouterService
)


def extract_competitive_intelligence(
    topic,
    evidence,
    signals,
    known_competitors=None
):

    known_competitors = (
        known_competitors
        or
        []
    )

    competitive_evidence = [

        {
            "title":
            item.get(
                "title",
                ""
            ),

            "snippet":
            item.get(
                "snippet",
                ""
            )
        }

        for item in evidence

    ][:10]

    competitive_context = {

        "competitive":
        signals.get(
            "competitive",
            {}
        )
    }

    prompt = f"""
You are a senior competitive intelligence analyst.

Topic:
{topic}

Signals:
{competitive_context}

Known Competitors:
{known_competitors}

Evidence:
{competitive_evidence}

Your job is to identify:

1. Competitors
2. Competitive threats
3. Positioning gaps
4. White space opportunities
5. Differentiation opportunities

Definitions:

Competitor:
A company, product, or solution solving the same problem.

Competitive Threat:
Something that makes the market harder to enter.

Positioning Gap:
A customer need competitors are not serving well.

White Space Opportunity:
An underserved market area with strong potential.

Differentiation Opportunity:
A way to stand apart from competitors.

Rules:

- Base conclusions ONLY on provided evidence.
- Use known competitors when relevant.
- Do not invent competitors.
- Ignore unrelated evidence.
- Rank strongest insights first.
- Return ONLY valid JSON.

Confidence Rules:

1 source:
max confidence = 50

2-3 sources:
max confidence = 75

4+ sources:
max confidence = 90

No evidence:
confidence = 0

Schema:

{{
  "competitors": [
    {{
      "name": "",
      "strength": 0
    }}
  ],

  "competitive_threats": [
    {{
      "name": "",
      "severity": 0
    }}
  ],

  "positioning_gaps": [
    {{
      "name": "",
      "opportunity": 0
    }}
  ],

  "white_space_opportunities": [
    {{
      "name": "",
      "score": 0
    }}
  ],

  "differentiation_opportunities": [
    {{
      "name": "",
      "score": 0
    }}
  ]
}}

Additional Requirements:

- Maximum 5 items per category.
- Use concise names.
- Rank highest-confidence items first.

CRITICAL JSON RULES:

- Every score MUST be an integer.
- Every numeric field MUST be a valid JSON number.
- All scores must be between 0 and 100.

VALID:
60

INVALID:
"60"
sixty
high
medium

Output valid JSON only.
"""

    print("  calling competitive intelligence")

    return OpenRouterService().call_json(prompt)