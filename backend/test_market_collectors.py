# test_market_reports.py

import asyncio

from app.collectors.market_reports_collector import (
    MarketReportsCollector
)


async def main():

    collector = MarketReportsCollector()

    results = await collector.collect(
        "AI Nutrition Coach"
    )

    print()

    print(
        "RESULT COUNT:",
        len(results)
    )

    print()

    for item in results[:10]:

        print("=" * 60)

        print(
            "TITLE:",
            item["title"]
        )

        print(
            "QUERY:",
            item["query"]
        )

        print(
            "SNIPPET:",
            item["snippet"]
        )

        print(
            "URL:",
            item["url"]
        )

        print()


asyncio.run(main())