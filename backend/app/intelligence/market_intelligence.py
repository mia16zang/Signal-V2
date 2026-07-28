from app.services.openrouter_service import (
    OpenRouterService
)


def extract_market_intelligence(
    topic,
    evidence,
    signals
):

    market_evidence = [

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

    market_context = {

        "market":
        signals.get(
            "market",
            {}
        ),

        "market_opportunity":
        signals.get(
            "market_opportunity",
            {}
        ),

        "market_size":
        signals.get(
            "market_size",
            {}
        )
    }

    prompt = f"""
You are a senior market intelligence analyst.

Topic:
{topic}

Signals:
{market_context}

Detected Market Sizes:
{market_context.get("market_opportunity", {}).get("detected_market_sizes", [])}

Detected Growth Rates:
{market_context.get("market_opportunity", {}).get("detected_growth_rates", [])}

Evidence:
{market_evidence}

Your goal is to estimate:

1. Market opportunity
2. Market growth
3. Market maturity
4. Key trends
5. Emerging trends
6. Market drivers
7. Future outlook

Definitions:

Market Size:
Use detected market sizes when available.

Growth Rate:
Use detected growth rates when available.

Market Maturity:
Must be one of:

- Emerging
- Growth
- Mature
- Declining

Key Trend:
Already impacting the market.

Emerging Trend:
Likely to become important in the next 1-3 years.

Market Driver:
A force causing adoption or growth.

Future Outlook:
Expected market direction over the next 12-24 months.

Rules:

- Base conclusions ONLY on provided evidence.
- Prefer extracted market sizes and growth rates over assumptions.
- If evidence is weak, lower confidence.
- Rank strongest trends first.
- Scores must be 0-100.
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
  "market_size": {{
    "estimate": "",
    "confidence": 0
  }},

  "growth_rate": {{
    "estimate": "",
    "confidence": 0
  }},

  "market_maturity": {{
    "stage": "",
    "confidence": 0
  }},

  "future_outlook": {{
    "direction": "",
    "confidence": 0
  }},

  "key_trends": [
    {{
      "name": "",
      "strength": 0
    }}
  ],

  "emerging_trends": [
    {{
      "name": "",
      "potential": 0
    }}
  ],

  "market_drivers": [
    {{
      "name": "",
      "impact": 0
    }}
  ]
}}

Additional Requirements:

- Return 5-10 trends when evidence supports it.
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

    print("CALLING MARKET OPENROUTER")

    service = OpenRouterService()

    result = service.call_json(
    prompt,
    debug=True
)

    print("\nFINAL RESULT:")
    print(result)

    return result