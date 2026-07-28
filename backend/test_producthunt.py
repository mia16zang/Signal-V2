import asyncio
from app.collectors.producthunt_collector import ProductHuntCollector


async def main():

    collector = ProductHuntCollector()

    results = await collector.collect(
        "AI Nutrition Coach"
    )

    print(results[0])

asyncio.run(main())