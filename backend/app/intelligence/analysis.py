from app.intelligence.signals import generate_market_pulse
from app.intelligence.opportunities import generate_opportunities
from app.intelligence.threats import generate_threats


def analyze_market(evidence):

    pulse = generate_market_pulse(evidence)

    opportunities = generate_opportunities(
        pulse
    )

    threats = generate_threats(
        pulse
    )

    return {
    "market_pulse": pulse.model_dump(),
    "opportunities": opportunities,
    "threats": threats
}