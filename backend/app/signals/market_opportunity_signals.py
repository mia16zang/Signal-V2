import re


def extract(
    evidence
):

    market_size_mentions = 0
    growth_mentions = 0
    forecast_mentions = 0
    cagr_mentions = 0

    billion_mentions = 0
    million_mentions = 0
    detected_market_sizes = []
    detected_growth_rates = []

    for item in evidence:

        if item.get(
            "source"
        ) != "market_report":

            continue

        text = (
            item.get(
                "title",
                ""
            )
            +
            " "
            +
            item.get(
                "snippet",
                ""
            )
        ).lower()
        
        market_size_matches = re.findall(
            r"\$\d+(?:\.\d+)?\s*(?:billion|million|b|m)",
            text,
            re.IGNORECASE
        )

        detected_market_sizes.extend(
        market_size_matches
        )
        
        growth_matches = re.findall(
            r"\d+(?:\.\d+)?%",
            text
        )

        detected_growth_rates.extend(
        growth_matches
        )

        if (
            "market size"
            in text
        ):

            market_size_mentions += 1

        if (
            "growth"
            in text
            or
            "growing"
            in text
            or
            "expansion"
            in text
        ):

            growth_mentions += 1

        if (
            "forecast"
            in text
            or
            "projected"
            in text
            or
            "expected to reach"
            in text
            or
            "predicted"
            in text
        ):

            forecast_mentions += 1

        if (
            "cagr"
            in text
        ):

            cagr_mentions += 1

        if (
            "billion"
            in text
            or
            re.search(
                r"\$\d+(\.\d+)?\s*b",
                text
            )
        ):

            billion_mentions += 1

        if (
            "million"
            in text
            or
            re.search(
                r"\$\d+(\.\d+)?\s*m",
                text
            )
        ):

            million_mentions += 1

    opportunity_score = min(
        100,
        (
            market_size_mentions * 10
            +
            growth_mentions * 8
            +
            forecast_mentions * 10
            +
            cagr_mentions * 12
            +
            billion_mentions * 15
            +
            million_mentions * 5
        )
    )
    
    detected_market_sizes = list(
    set(
        detected_market_sizes
    )
    )

    detected_growth_rates = list(
    set(
        detected_growth_rates
    )
    )

    return {

        "market_size_mentions":
        market_size_mentions,

        "growth_mentions":
        growth_mentions,

        "forecast_mentions":
        forecast_mentions,

        "cagr_mentions":
        cagr_mentions,

        "billion_mentions":
        billion_mentions,

        "million_mentions":
        million_mentions,
        
        "detected_market_sizes":
        detected_market_sizes,

        "detected_growth_rates":
        detected_growth_rates,

        "opportunity_score":
        opportunity_score
    }