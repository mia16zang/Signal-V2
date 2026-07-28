# market_signals.py

def extract(evidence):

    growth_score = 0

    startup_activity = 0

    for item in evidence:

        if item.get("source") =="google_trends":

            growth_score = item.get(
                "growth_rate",
                0
            )

        if item.get("source") =="producthunt":

            startup_activity += 1

    return {

        "growth_score":
        growth_score,

        "startup_activity":
        startup_activity
    }