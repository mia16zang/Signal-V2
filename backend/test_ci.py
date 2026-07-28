# test_competitive_intelligence.py

from app.intelligence.competitive_intelligence import (
    extract_competitive_intelligence
)

result = extract_competitive_intelligence(

    topic="AI Nutrition Coach",

    evidence=[

        {
            "source": "producthunt",
            "title": "AI Nutrition Assistant",
            "snippet": "Personalized nutrition coaching"
        },

        {
            "source": "youtube",
            "title": "How I Lost 50 Pounds with ChatGPT"
        },

        {
            "source": "market_report",
            "title": "Personalized Nutrition Market Growth"
        }

    ],

    signals={
        "competitive": {
            "competition_score": 72
        }
    },
    
    known_competitors=[
        "Noom",
        "MyFitnessPal",
        "Cronometer",
        "Whoop"
    ]
    
      
)

print(result)
