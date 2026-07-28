# test_intelligence_engine.py

from app.intelligence.intelligence_engine import (
    build_intelligence
)

topic = "AI Nutrition Coach"

evidence = [

    {
        "source": "youtube",
        "title": "How I Lost 50 Pounds with ChatGPT",
        "views": 190657,
        "likes": 7192
    },

    {
        "source": "google_trends",
        "title": "AI Nutrition Coach",
        "growth_rate": 18
    },

    {
        "source": "producthunt",
        "title": "NomNak",
        "snippet": "Find restaurants through people you trust",
        "votes": 137,
        "comments": 22
    },

    {
        "source": "market_report",
        "title": "AI Nutrition Market Expected to Reach $8.2 Billion by 2030",
        "snippet": "Forecast CAGR 18.4%"
    }
]

signals = {

    "virality": {
        "momentum": 78
    },

    "market_opportunity": {

        "opportunity_score": 82,

        "detected_market_sizes": [
            "$8.2 billion"
        ],

        "detected_growth_rates": [
            "18.4%"
        ]
    },

    "competitive": {
        "competition_score": 72
    }
}

known_competitors = [

    "Noom",
    "MyFitnessPal",
    "Cronometer",
    "Whoop"
]

result = build_intelligence(

    topic=topic,

    evidence=evidence,

    signals=signals,

    known_competitors=known_competitors
)

print("\n\nINTELLIGENCE OUTPUT\n")
print(result)