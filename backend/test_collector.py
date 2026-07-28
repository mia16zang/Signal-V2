from app.collectors.ddgs_collector import DDGSCollector
import asyncio

async def main():

    collector = DDGSCollector()

    results = await collector.collect(
        "Patek Philippe competitors",
        "Patek Philippe"
    )

    print(len(results))

    if results:
        print(results[0])

asyncio.run(main())