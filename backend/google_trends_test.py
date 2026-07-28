import asyncio
from app.collectors.google_trends_collector import GoogleTrendsCollector

async def main():

    collector = GoogleTrendsCollector()

    results = await collector.collect(
        "Artificial Intelligence"
    )

    print(results)

asyncio.run(main())