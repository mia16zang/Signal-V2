from app.intelligence.customer_intelligence import (
    extract_customer_intelligence
)

result = extract_customer_intelligence(

    topic="AI Nutrition Coach",

    evidence=[
        {
            "source":
            "youtube",

            "title":
            "How I Lost 50 Pounds with ChatGPT"
        }
    ],

    signals={
        "virality": {
            "momentum": 78
        }
    }
)

print(result)