from app.intelligence.signals import generate_market_pulse

fake_evidence = [
    {
        "title": "AI Nutrition Market Growth Surges",
        "snippet": "Demand increasing rapidly and adoption expanding."
    },
    {
        "title": "Nutrition startup raises $12M Series A",
        "snippet": "Funding announced by investors."
    },
    {
        "title": "Users love AI meal planning",
        "snippet": "Popular and rapidly growing category."
    },
    {
        "title": "MyFitnessPal competitor launches premium plan",
        "snippet": "New competitor enters market."
    }
]

pulse = generate_market_pulse(fake_evidence)

print("\nMARKET PULSE")
print("------------")
print(pulse)