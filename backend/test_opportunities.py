from app.intelligence.signals import (
    generate_market_pulse
)

from app.intelligence.opportunities import (
    generate_opportunities
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

pulse = generate_market_pulse(
    fake_evidence
)

print("PULSE:")
print(pulse)

opportunities = generate_opportunities(
    pulse
)
print("OPPORTUNITIES:")
print(opportunities)
print("Growth:", pulse.growth)
print("Competition:", pulse.competition)