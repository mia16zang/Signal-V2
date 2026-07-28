from app.collectors.ddgs_collector import (
    DDGSCollector
)

collector = DDGSCollector()


class AnalysisService:

    async def analyze(
        self,
        topic: str
    ):

        queries = [

            # Competition
            f"{topic} competitors",
            f"{topic} alternatives",

            # Customer sentiment
            f"{topic} customer complaints",
            f"{topic} reviews",
            f"{topic} complaints",

            # Market intelligence
            f"{topic} funding",
            f"{topic} startup launches",
            f"{topic} market trends",
            f"{topic} pricing",
            f"{topic} growth",

            # Community discussions
            f"site:reddit.com {topic}",
            f"site:youtube.com {topic}"
        ]

        evidence = []

        for query in queries:

            results = await collector.collect(
                query,
                topic
            )

            evidence.extend(results)

        # Remove duplicate URLs
        unique_evidence = []
        seen_urls = set()

        for item in evidence:

            url = item.get(
                "url",
                ""
            )

            if url in seen_urls:
                continue

            seen_urls.add(url)

            unique_evidence.append(
                item
            )

        return {
            "topic": topic,
            "evidence_count": len(
                unique_evidence
            ),
            "evidence": unique_evidence
        }
