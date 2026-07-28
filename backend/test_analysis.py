from app.intelligence.analysis import (
    analyze_market
)

fake_evidence = [
    {
        "title":
        "AI Nutrition Market Growth Surges",

        "snippet":
        "Demand increasing rapidly."
    },

    {
        "title":
        "Startup raises $12M Series A",

        "snippet":
        "Funding announced."
    }
]

result = analyze_market(
    fake_evidence
)

print(result)