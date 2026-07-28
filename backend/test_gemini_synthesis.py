import time

from app.pipeline.analyze_topic import (
    analyze_topic
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


print("\nRUNNING ANALYSIS...\n")

start = time.time()

result = analyze_topic(

    topic=topic,

    evidence=evidence,

    signals=signals,

    known_competitors=known_competitors
)

print(
    "\nTOTAL TIME:",
    round(
        time.time() - start,
        2
    ),
    "seconds"
)

print("\nRESULT:\n")

print(result)