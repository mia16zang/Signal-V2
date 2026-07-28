from app.intelligence.customer_intelligence import (
    extract_customer_intelligence
)

from app.intelligence.market_intelligence import (
    extract_market_intelligence
)

from app.intelligence.competitive_intelligence import (
    extract_competitive_intelligence
)


def build_intelligence(
    topic,
    evidence,
    signals,
    known_competitors=None
):

    print("\nBUILD_INTELLIGENCE START")

    customer = extract_customer_intelligence(
        topic,
        evidence,
        signals
    )

    print("\nCUSTOMER:")
    print(customer)

    market = extract_market_intelligence(
        topic,
        evidence,
        signals
    )

    print("\nMARKET:")
    print(market)

    competitive = extract_competitive_intelligence(
        topic,
        evidence,
        signals,
        known_competitors or []
    )

    print("\nCOMPETITIVE:")
    print(competitive)

    return {
        "customer": customer,
        "market": market,
        "competitive": competitive
    }