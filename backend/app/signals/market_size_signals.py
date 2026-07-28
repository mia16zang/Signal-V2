# market_size_signals.py

def extract(evidence):

    reports = 0

    for item in evidence:

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

        if (
            "market size" in text
            or
            "market forecast" in text
            or
            "industry report" in text
        ):

            reports += 1

    return {

        "market_reports":
        reports
    }