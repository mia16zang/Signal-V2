def generate_threats(
    market_pulse
):

    threats = []

    if (
        market_pulse.competition > 5
    ):

        threats.append(
            {
                "title":
                "High Competition",

                "impact":
                85,

                "confidence":
                80,

                "reason":
                "Market becoming crowded"
            }
        )

    if (
        market_pulse.sentiment < 60
    ):

        threats.append(
            {
                "title":
                "Negative Customer Sentiment",

                "impact":
                75,

                "confidence":
                70,

                "reason":
                "Customers expressing dissatisfaction"
            }
        )

    if (
        market_pulse.pricing_power < 60
    ):

        threats.append(
            {
                "title":
                "Weak Pricing Power",

                "impact":
                65,

                "confidence":
                75,

                "reason":
                "Customers appear price sensitive"
            }
        )

    return threats