from ddgs import DDGS

from app.collectors.ddgs_collector import DDGSCollector
import asyncio

async def main():

    collector = DDGSCollector()

    results = await collector.collect(
        "AI Nutrition Coach competitors"
    )

    print(results)

asyncio.run(main())