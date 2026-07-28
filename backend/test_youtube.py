# test_youtube_v2.py

import asyncio

from app.collectors.youtube_collector import (
    YouTubeCollector
)

async def main():

    collector = YouTubeCollector()

    results = await collector.collect(
        "AI Nutrition Coach"
    )

    print()

    print(
        "RESULTS:",
        len(results)
    )

    print()

    for item in results[:3]:

        print("=" * 60)

        print("TITLE:", item["title"])

        print("VIEWS:", item["views"])

        print("LIKES:", item["likes"])

        print("COMMENTS:", item["comments"])

        print("AGE DAYS:", item["age_days"])

        print(
            "VIEWS/DAY:",
            item["views_per_day"]
        )

        print(
            "ENGAGEMENT RATE:",
            item["engagement_rate"],
            "%"
        )

        print()

asyncio.run(main())