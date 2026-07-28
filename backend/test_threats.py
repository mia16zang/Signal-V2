from app.intelligence.signals import (
    generate_market_pulse
)

from app.intelligence.threats import (
    generate_threats
)

fake_evidence = [
    {
        "title":
        "Users complain about expensive subscriptions",

        "snippet":
        "Many negative reviews reported."
    }
]

pulse = generate_market_pulse(
    fake_evidence
)

threats = generate_threats(
    pulse
)

print(threats)