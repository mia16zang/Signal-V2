from app.services.gemini_service import (
    GeminiService
)

from app.synthesis.compress_intelligence import (
    compress_intelligence
)


def generate_synthesis(
    topic,
    intelligence,
    signals
):

    compressed = compress_intelligence(
        intelligence
    )

    executive_intelligence = {

        "top_segments":
        compressed["customer"][
            "segments"
        ],

        "top_pain_points":
        compressed["customer"][
            "pain_points"
        ],

        "top_desired_outcomes":
        compressed["customer"][
            "desired_outcomes"
        ],

        "market_size":
        compressed["market"][
            "market_size"
        ],

        "growth_rate":
        compressed["market"][
            "growth_rate"
        ],

        "market_maturity":
        compressed["market"][
            "market_maturity"
        ],

        "future_outlook":
        compressed["market"][
            "future_outlook"
        ],

        "top_trends":
        compressed["market"][
            "key_trends"
        ],

        "top_competitors":
        compressed["competitive"][
            "competitors"
        ],

        "top_positioning_gaps":
        compressed["competitive"][
            "positioning_gaps"
        ],

        "top_white_space":
        compressed["competitive"][
            "white_space"
        ],

        "top_differentiators":
        compressed["competitive"][
            "differentiation"
        ],

        "signals":
        signals
    }

    prompt = f"""
You are a world-class venture capitalist,
startup strategist,
and market analyst.

Topic:
{topic}

Executive Intelligence:
{executive_intelligence}

Your job is NOT to summarize.

Your job is to determine:

- Whether this market is attractive
- Whether a startup should enter
- Why now is the right or wrong time
- How a startup could differentiate
- What customer segment should be targeted first
- Key opportunities
- Key risks
- Potential moats

Rules:

- Think like a startup founder.
- Think like a venture capitalist.
- Use ONLY provided intelligence.
- Prefer uncertainty over fabrication.
- Do not invent statistics.
- Do not invent scores.
- Do not invent confidence values.
- Do not invent market sizes.
- Do not invent competitor scores.
- Do not invent customer scores.
- Never cite a number unless it exists in the provided intelligence.
- Executive summary maximum 3 sentences.
- Keep every reason under 25 words.
- Keep every evidence field under 15 words.
- Confidence must be between 0 and 95.
- Opportunity scores above 90 should be extremely rare.
- Return ONLY valid JSON.
- Every recommendation MUST be supported by intelligence.
- Never invent a customer segment.
- Use the highest scoring customer segment when recommending customers.
- If evidence strongly indicates weight loss, prefer weight-loss seekers.

CRITICAL:

If a numerical score is not explicitly present in the provided intelligence,
DO NOT create one.

Bad:
"MyFitnessPal (95)"

Good:
"MyFitnessPal"

Bad:
"Weight loss seekers (95)"

Good:
"Weight loss seekers"

Bad:
"Trend strength 87"

Good:
"Strong trend"

Only use numbers that already exist in the provided intelligence.

Evidence Rules:

- If evidence is weak, reduce confidence.
- If evidence is missing, state uncertainty.
- Never invent signal scores.
- Never invent customer data.
- Never invent market statistics.
- Never invent competitor data.

Scoring Guide:

Opportunity Score

0-40:
Weak opportunity

41-60:
Uncertain opportunity

61-80:
Promising opportunity

81-90:
Strong opportunity

91-95:
Exceptional opportunity

Market Pulse should consider:

- Market growth
- Customer demand
- Competitive intensity
- Trend momentum

Build Recommendation must be one of:

- Strong Yes
- Yes
- Monitor
- No


Schema:

{{
  "market_pulse": 0,

  "opportunity_score": 0,

  "build_recommendation": {{
    "decision": "",
    "reason": ""
  }},

  "confidence": 0,

  "confidence_explanation": "",

  "top_reason_to_build": "",

  "biggest_risk": "",

  "best_customer_segment": "",

  "best_moat": "",

  "executive_summary": "",

  "why_now": [
    {{
      "title": "",
      "evidence": "",
      "reason": ""
    }}
  ],

  "key_opportunities": [
    {{
      "title": "",
      "evidence": "",
      "reason": ""
    }}
  ],

  "key_risks": [
    {{
      "title": "",
      "evidence": "",
      "reason": ""
    }}
  ],

  "recommended_customer": "",

  "recommended_positioning": "",

  "potential_moats": [
    {{
      "title": "",
      "evidence": "",
      "reason": ""
    }}
  ],

  "execution_ideas": [
    {{
      "title": "",
      "reason": ""
    }}
  ]
}}

Additional Requirements:

- Maximum 3 why_now items
- Maximum 3 opportunities
- Maximum 3 risks
- Maximum 3 moats
- Maximum 3 execution ideas
- Rank strongest items first
- Use concise titles
- Use concise evidence
- Use concise reasons
- Return valid JSON only
"""

    print(
        "EXECUTIVE INTELLIGENCE SIZE:",
        len(
            str(
                executive_intelligence
            )
        )
    )

    print(
        "PROMPT SIZE:",
        len(prompt)
    )

    service = GeminiService()

    return service.call_json(
        prompt
    )