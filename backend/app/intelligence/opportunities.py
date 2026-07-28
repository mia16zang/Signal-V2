def generate_opportunities(
    market_pulse
):

    opportunities = []

    if market_pulse.growth > 50:

        opportunities.append(
            {
                "title":
                "Growing Market Demand",

                "score":
                85,

                "confidence":
                80,

                "reason":
                "Strong growth signals detected"
            }
        )

    if market_pulse.funding > 50:

        opportunities.append(
            {
                "title":
                "Investor Interest",

                "score":
                80,

                "confidence":
                75,

                "reason":
                "Funding activity indicates market validation"
            }
        )

    if market_pulse.sentiment > 60:

        opportunities.append(
            {
                "title":
                "Positive Customer Reception",

                "score":
                75,

                "confidence":
                80,

                "reason":
                "Customer sentiment appears favorable"
            }
        )

    if (
        market_pulse.growth > 50
        and
        market_pulse.sentiment > 60
    ):

        opportunities.append(
            {
                "title":
                "Expansion Opportunity",

                "score":
                90,

                "confidence":
                85,

                "reason":
                "Growth and sentiment are both strong"
            }
        )

    return opportunities