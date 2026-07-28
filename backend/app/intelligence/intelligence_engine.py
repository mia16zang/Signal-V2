"""Legacy three-call extraction path. Used only when PORTFOLIO_MODE is False.

Kept intact so the original behaviour is still reachable, with two fixes
applied: the results are passed through the same contract normaliser the
merged path uses, and the per-call debug dumps are off (they printed 5000
characters of raw model output plus the parsed dict, three times per request).
"""

from app.intelligence.competitive_intelligence import extract_competitive_intelligence
from app.intelligence.customer_intelligence import extract_customer_intelligence
from app.intelligence.market_intelligence import extract_market_intelligence
from app.services.json_utils import (
    normalise_competitive,
    normalise_customer,
    normalise_market,
)


def build_intelligence(topic, evidence, signals, known_competitors=None):
    return {
        "customer": normalise_customer(
            extract_customer_intelligence(topic, evidence, signals)
        ),
        "market": normalise_market(
            extract_market_intelligence(topic, evidence, signals)
        ),
        "competitive": normalise_competitive(
            extract_competitive_intelligence(
                topic, evidence, signals, known_competitors or []
            )
        ),
    }
