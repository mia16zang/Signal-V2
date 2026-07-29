"""Collection and orchestration.

Three changes:

1. The cache is checked before anything runs. It used to be checked inside
   `analyze_topic`, which is called after collection has already finished --
   so a cache hit still paid the full ~39s of searching before returning a
   stored answer. Repeat topics are now sub-second.

2. Collectors run concurrently. They were sequential, and because each
   `collect` was `async def` wrapping fully synchronous work, they also
   blocked the event loop for the whole request.

3. Evidence is ranked and capped instead of being passed on whole. The cap
   is not a speed optimisation -- the prompt only ever used a slice, so the
   count never affected LLM time. It is a quality one: it decides *which*
   items reach the model.
"""

import asyncio
import time

from app import config
from app.collectors.ddgs_collector import DDGSCollector
from app.collectors.google_trends_collector import GoogleTrendsCollector
from app.collectors.producthunt_collector import ProductHuntCollector
from app.collectors.youtube_collector import YouTubeCollector
from app.pipeline.analyze_topic import analyze_topic
from app.services.cache_service import CacheService
from app.signals.signal_engine import build_signals

ddgs = DDGSCollector()
youtube = YouTubeCollector()
google_trends = GoogleTrendsCollector()
producthunt = ProductHuntCollector()


async def _guarded(name, coro, timeout):
    """Run a collector, never let it fail or stall the whole request."""
    started = time.time()
    try:
        result = await asyncio.wait_for(coro, timeout=timeout)
        print(f"  {name}: {len(result)} items in {time.time() - started:.1f}s")
        return result
    except asyncio.TimeoutError:
        print(f"  {name}: TIMEOUT after {timeout}s, skipped")
        return []
    except Exception as e:
        print(f"  {name}: {type(e).__name__}: {str(e)[:150]}")
        return []


def _score(item, topic_words):
    """Cheap relevance heuristic. No model call, no network."""
    title = (item.get("title") or "").lower()
    snippet = (item.get("snippet") or "").lower()
    text = title + " " + snippet

    score = 0

    # Topic terms, weighted toward the title.
    for word in topic_words:
        if word in title:
            score += 12
        elif word in snippet:
            score += 5

    # Substance: a one-line snippet rarely supports a conclusion.
    length = len(snippet)
    score += min(length // 60, 8)

    # Terms that map onto what the prompt actually asks for.
    for term, weight in (
        ("review", 6), ("vs", 5), ("alternative", 6), ("complaint", 7),
        ("problem", 5), ("best", 4), ("market", 6), ("growth", 5),
        ("cagr", 8), ("forecast", 6), ("funding", 6), ("raised", 6),
        ("pricing", 5), ("competitor", 7),
    ):
        if term in text:
            score += weight

    # A dollar figure or a percentage is what the market section needs.
    if "$" in text:
        score += 6
    if "%" in text:
        score += 5

    # Non-search sources carry structured numbers the signal layer reads.
    if item.get("source") in ("youtube", "producthunt", "google_trends"):
        score += 10

    return score


def rank_evidence(evidence, topic, limit):
    """Rank, then interleave by query so one query cannot dominate.

    A pure top-N sort tends to return eight variations of the same "best X"
    listicle. Round-robining across the originating queries preserves the
    breadth that made the query list worth running.
    """
    words = [w for w in topic.lower().split() if len(w) > 2]

    buckets = {}
    for item in evidence:
        buckets.setdefault(item.get("query", item.get("source", "")), []).append(item)

    for items in buckets.values():
        items.sort(key=lambda i: _score(i, words), reverse=True)

    ordered = []
    for row in range(max((len(v) for v in buckets.values()), default=0)):
        for items in buckets.values():
            if row < len(items):
                ordered.append(items[row])

    return ordered[:limit]


class AnalysisService:

    async def collect(self, topic):
        tasks = [
            # collect_many enforces the real budget per query, so this outer
            # guard is only a backstop against the gather itself wedging. At
            # exactly COLLECTOR_TIMEOUT_SECONDS it would fire first and throw
            # away the queries that did finish -- which is the failure this
            # per-query timeout exists to prevent.
            _guarded(
                "ddgs",
                ddgs.collect_many(config.search_queries(topic), topic),
                config.COLLECTOR_TIMEOUT_SECONDS + 5,
            )
        ]

        if config.ENABLE_YOUTUBE:
            tasks.append(
                _guarded("youtube", youtube.collect(topic),
                         config.COLLECTOR_TIMEOUT_SECONDS)
            )

        if config.ENABLE_GOOGLE_TRENDS:
            tasks.append(
                _guarded("google_trends", google_trends.collect(topic),
                         config.COLLECTOR_TIMEOUT_SECONDS)
            )

        if config.ENABLE_PRODUCT_HUNT:
            tasks.append(
                _guarded("producthunt", producthunt.collect(topic),
                         config.COLLECTOR_TIMEOUT_SECONDS)
            )

        batches = await asyncio.gather(*tasks)

        evidence = []
        seen = set()
        for batch in batches:
            for item in batch:
                url = item.get("url", "")
                if url and url in seen:
                    continue
                if url:
                    seen.add(url)
                evidence.append(item)

        return evidence

    async def analyze(self, topic):
        request_start = time.time()

        print(f"\n{'=' * 58}\nANALYZE: {topic}\n{config.describe()}\n{'=' * 58}")

        # Before collection, not after. This is the whole point of a cache.
        if config.CACHE_ENABLED:
            cached = CacheService.get(topic)
            if cached:
                elapsed = time.time() - request_start
                if "meta" in cached:
                    cached["meta"]["cached"] = True
                print(f"CACHE HIT -- served in {elapsed:.2f}s\n")
                return cached

        collect_start = time.time()
        raw_evidence = await self.collect(topic)
        collection_time = round(time.time() - collect_start, 2)

        evidence = rank_evidence(raw_evidence, topic, config.MAX_EVIDENCE_ITEMS)

        breakdown = {}
        for item in evidence:
            source = item.get("source", "unknown")
            breakdown[source] = breakdown.get(source, 0) + 1

        print(
            f"Collection: {collection_time}s "
            f"({len(raw_evidence)} raw -> {len(evidence)} ranked) {breakdown}"
        )

        signals = build_signals(evidence)

        result = await asyncio.to_thread(
            analyze_topic,
            topic=topic,
            evidence=evidence,
            signals=signals,
            known_competitors=[],
            collection_time=collection_time,
        )

        total = round(time.time() - request_start, 2)
        result["meta"]["total_time"] = total

        print(f"Total: {total}s\n")

        if config.CACHE_ENABLED:
            CacheService.set(topic, result)

        return result
