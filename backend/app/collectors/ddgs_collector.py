"""DuckDuckGo collector.

The old collector ran one search per call, each opening its own DDGS client,
and `AnalysisService` awaited them one at a time. `collect` was declared
`async` but its body was fully synchronous, so `await` yielded nothing --
twelve searches ran strictly back to back.

Measured on the live API, 12 searches for one topic:

    sequential, client per query   38.9s   (median 3.2s per search)
    concurrent via to_thread        5.2s

Wall time is bounded by the slowest single search, not by how many run, so
the query list stays broad. Trimming it to 5 measured 5.8s -- no faster.
"""

import asyncio

from ddgs import DDGS

from app import config


def is_relevant(result, topic_words) -> bool:
    if not topic_words:
        return True
    text = (result.get("title", "") + " " + result.get("body", "")).lower()
    return any(word in text for word in topic_words)


def _topic_words(topic: str):
    return [w for w in topic.lower().split() if len(w) > 2]


def _search(query: str, topic_words, max_results: int):
    """Blocking. Runs on a worker thread."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception as e:
        print(f"  ddgs error [{query}]: {type(e).__name__}: {str(e)[:120]}")
        return []

    out = []
    for result in results:
        if not is_relevant(result, topic_words):
            continue
        out.append({
            "source": "ddgs",
            "title": result.get("title", ""),
            "url": result.get("href", ""),
            "snippet": result.get("body", ""),
            "query": query,
        })
    return out


class DDGSCollector:

    async def collect_many(self, queries, topic):
        """Run every query concurrently and return one flat, de-duplicated list.

        De-duplication happens here rather than downstream because the query
        set overlaps by design -- "competitors alternatives" and "reviews
        complaints" surface the same landing pages. Deduping at the source
        means the ranking step downstream sees real breadth, not repeats.

        Each query carries its own timeout. It used to have none: the caller
        wrapped this whole coroutine in a single `wait_for`, so one slow search
        past the budget discarded all eight, and the request fell back to
        YouTube alone. Observed live -- `ddgs: TIMEOUT after 12s, skipped`,
        collection 12.0s, 11 items, zero web sources to cite.

        The batch is only as slow as its slowest survivor either way. The
        difference is that a straggler now costs one query instead of all of
        them.
        """
        words = _topic_words(topic)

        async def one(query):
            return await asyncio.wait_for(
                asyncio.to_thread(_search, query, words, config.DDGS_MAX_RESULTS),
                timeout=config.COLLECTOR_TIMEOUT_SECONDS,
            )

        batches = await asyncio.gather(
            *[one(q) for q in queries],
            return_exceptions=True,
        )

        merged = []
        seen = set()
        timed_out = 0

        for query, batch in zip(queries, batches):
            if isinstance(batch, asyncio.TimeoutError):
                timed_out += 1
                continue
            if isinstance(batch, BaseException):
                print(f"  ddgs batch failed [{query}]: {batch!r}")
                continue
            for item in batch:
                url = item.get("url", "")
                if url and url in seen:
                    continue
                if url:
                    seen.add(url)
                merged.append(item)

        if timed_out:
            print(
                f"  ddgs: {timed_out}/{len(queries)} queries timed out after "
                f"{config.COLLECTOR_TIMEOUT_SECONDS}s, kept {len(merged)} items"
            )

        return merged

    async def collect(self, query: str, topic: str):
        """Single-query form, kept for the existing test scripts."""
        return await asyncio.to_thread(
            _search, query, _topic_words(topic), config.DDGS_MAX_RESULTS
        )
