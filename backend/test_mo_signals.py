from app.signals.market_opportunity_signals import (
    extract
)

sample = [

    {
        "source":
        "market_report",

        "title":
        "AI Nutrition Market Expected to Reach $8.2 Billion by 2030",

        "snippet":
        "The market is forecast to grow at 18.4% CAGR."
    },

    {
        "source":
        "market_report",

        "title":
        "Nutrition Technology Market Size Report",

        "snippet":
        "Industry projected to reach $950 million."
    }
]

print(
    extract(
        sample
    )
)