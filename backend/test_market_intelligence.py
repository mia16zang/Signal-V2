# test_market_intelligence.py

from app.intelligence.market_intelligence import (
    extract_market_intelligence
)

result = extract_market_intelligence(

    topic="AI Nutrition Coach",

    evidence=[
        {
            "source": "google_trends",
            "growth_rate": 18
        },
        {
            "source": "youtube",
            "title": "How I Lost 50 Pounds with ChatGPT"
        },
        {
            "source": "producthunt",
            "title": "AI Health App"
        }
    ],

    signals={
        "market": {
            "growth_score": 18
        }
    }
)

print(result)