from app.collectors.ddgs_collector import DDGSCollector
from app.intelligence.analysis import analyze_market

import asyncio


async def main():

    print("Starting collector...")

    collector = DDGSCollector()

    queries = [
        "Patek Philippe competitors",
        "Patek Philippe market trends",
        "Patek Philippe pricing",
        "Patek Philippe customer reviews",
        "Patek Philippe launches"
    ]

    evidence = []

    for query in queries:

        results = await collector.collect(
            query,
            "Patek Philippe"
        )

        evidence.extend(results)

    print("Evidence collected:", len(evidence))

    print("Running analysis...")

    result = analyze_market(
        evidence
    )

    print("Analysis complete")
    print(result)


asyncio.run(main())