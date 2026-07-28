from app.collectors.ddgs_collector import (
    DDGSCollector
)

from app.collectors.youtube_collector import (
    YouTubeCollector
)

from app.collectors.google_trends_collector import (
    GoogleTrendsCollector
)

from app.collectors.producthunt_collector import (
    ProductHuntCollector
)

from app.signals.signal_engine import (
    build_signals
)

from app.pipeline.analyze_topic import (
    analyze_topic
)


ddgs = DDGSCollector()

youtube = YouTubeCollector()

google_trends = (
    GoogleTrendsCollector()
)

producthunt = (
    ProductHuntCollector()
)


class AnalysisService:

    async def analyze(
        self,
        topic: str
    ):

        print(
            "\nSTEP 1: START COLLECTION"
        )

        evidence = []

        #
        # DDGS
        #

        queries = [

            f"{topic} competitors",
            f"{topic} alternatives",

            f"{topic} customer complaints",
            f"{topic} reviews",
            f"{topic} complaints",

            f"{topic} funding",
            f"{topic} startup launches",
            f"{topic} market trends",
            f"{topic} pricing",
            f"{topic} growth",

            f"site:reddit.com {topic}",
            f"site:youtube.com {topic}"
        ]

        for query in queries:

            results = await ddgs.collect(
                query,
                topic
            )

            evidence.extend(
                results
            )

        print(
            f"DDGS RESULTS: {len(evidence)}"
        )

        #
        # YouTube
        #

        youtube_results = (
            await youtube.collect(
                topic
            )
        )

        evidence.extend(
            youtube_results
        )

        print(
            f"YOUTUBE RESULTS: {len(youtube_results)}"
        )

        #
        # Google Trends
        #

        trends_results = (
            await google_trends.collect(
                topic
            )
        )

        evidence.extend(
            trends_results
        )

        print(
            f"GOOGLE TRENDS RESULTS: {len(trends_results)}"
        )

        #
        # Product Hunt
        #

        producthunt_results = (
            await producthunt.collect(
                topic
            )
        )

        evidence.extend(
            producthunt_results
        )

        print(
            f"PRODUCT HUNT RESULTS: {len(producthunt_results)}"
        )

        print(
            "\nSTEP 2: COLLECTION COMPLETE"
        )

        unique_evidence = []

        seen_urls = set()

        for item in evidence:

            url = item.get(
                "url",
                ""
            )

            if url and url in seen_urls:
                continue

            if url:
                seen_urls.add(
                    url
                )

            unique_evidence.append(
                item
            )

        print(
            "\nSTEP 3: UNIQUE EVIDENCE:",
            len(unique_evidence)
        )

        #
        # Debug source breakdown
        #

        sources = {}

        for item in unique_evidence:

            source = item.get(
                "source",
                "unknown"
            )

            sources[source] = (
                sources.get(
                    source,
                    0
                )
                + 1
            )

        print(
            "\nSOURCE BREAKDOWN:"
        )

        print(
            sources
        )

        signals = build_signals(
            unique_evidence
        )

        print(
            "\nSTEP 4: SIGNALS BUILT"
        )

        known_competitors = []

        print(
            "\nSTEP 5: RUNNING PIPELINE"
        )

        result = analyze_topic(

            topic=topic,

            evidence=unique_evidence,

            signals=signals,

            known_competitors=
            known_competitors
        )

        print(
            "\nSTEP 6: PIPELINE COMPLETE"
        )

        return result