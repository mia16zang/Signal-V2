from app.services.openrouter_service import (
    OpenRouterService
)


def extract_customer_intelligence(
    topic,
    evidence,
    signals
):
    customer_evidence = [

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

    customer_context = {

        "customer":
        signals.get(
            "customer",
            {}
        ),

        "virality":
        signals.get(
            "virality",
            {}
        )
    }

    prompt = f"""
You are a customer research analyst.

Topic:
{topic}

Signals:
{customer_context}

Evidence:
{customer_evidence}

Base conclusions ONLY on provided evidence.

Definitions:

Customer Segment:
A distinct group of users likely to buy this product.

Pain Point:
A frustration, unmet need, challenge, or obstacle experienced by customers.

Desired Outcome:
A result customers want to achieve.

Behavior Pattern:
An observable behavior, habit, or decision-making pattern.

Opportunity Area:
An underserved customer need, emerging trend, or market gap.

Rules:

- Base conclusions ONLY on provided evidence.
- Do not invent facts.
- Customer segments must be actual groups of people.
- Pain points must be real problems.
- Desired outcomes must be customer goals.
- Behavior patterns must be observable.
- Opportunity areas must be grounded in evidence.
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
  "customer_segments": [
    {{
      "name": "",
      "score": 0
    }}
  ],

  "pain_points": [
    {{
      "name": "",
      "signal_strength": 0
    }}
  ],

  "desired_outcomes": [
    {{
      "name": "",
      "importance": 0
    }}
  ],

  "behavior_patterns": [
    {{
      "name": "",
      "confidence": 0
    }}
  ],

  "opportunity_areas": [
    {{
      "name": "",
      "score": 0
    }}
  ]
}}

Additional Requirements:

- Return 5-10 items per category when evidence supports it.
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

    print("  calling customer intelligence")

    return OpenRouterService().call_json(prompt)