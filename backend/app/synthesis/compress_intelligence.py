# app/synthesis/compress_intelligence.py

def compress_intelligence(
    intelligence
):

    return {

        "customer": {

            "segments":
            intelligence["customer"].get(
                "customer_segments",
                []
            )[:3],

            "pain_points":
            intelligence["customer"].get(
                "pain_points",
                []
            )[:3],

            "desired_outcomes":
            intelligence["customer"].get(
                "desired_outcomes",
                []
            )[:3]
        },

        "market": {

            "market_size":
            intelligence["market"].get(
                "market_size",
                {}
            ),

            "growth_rate":
            intelligence["market"].get(
                "growth_rate",
                {}
            ),

            "market_maturity":
            intelligence["market"].get(
                "market_maturity",
                {}
            ),

            "future_outlook":
            intelligence["market"].get(
                "future_outlook",
                {}
            ),

            "key_trends":
            intelligence["market"].get(
                "key_trends",
                []
            )[:3]
        },

        "competitive": {

            "competitors":
            intelligence["competitive"].get(
                "competitors",
                []
            )[:3],

            "positioning_gaps":
            intelligence["competitive"].get(
                "positioning_gaps",
                []
            )[:3],

            "white_space":
            intelligence["competitive"].get(
                "white_space_opportunities",
                []
            )[:3],

            "differentiation":
            intelligence["competitive"].get(
                "differentiation_opportunities",
                []
            )[:3]
        }
    }