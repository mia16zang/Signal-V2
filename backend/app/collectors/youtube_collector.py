"""YouTube collector.

`collect` was `async def` wrapping entirely synchronous googleapiclient work,
so awaiting it blocked the event loop for its full duration -- which meant the
concurrent DDGS searches could not make progress while it ran. The blocking
work now happens on a worker thread and only the wrapper is async.
"""

import asyncio
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from googleapiclient.discovery import build

from app import config

load_dotenv()


def _age_days(published: str) -> int:
    """Whole days since publication, floored at 1 so it is safe to divide by."""
    if not published:
        return 1
    try:
        when = datetime.fromisoformat(published.replace("Z", "+00:00"))
    except ValueError:
        return 1
    return max(1, (datetime.now(timezone.utc) - when).days)


def _fetch(topic: str):
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print("  youtube: no YOUTUBE_API_KEY set, skipping")
        return []

    try:
        # cache_discovery=False avoids a filesystem discovery-doc cache that
        # warns and stats the disk on every build() call.
        youtube = build(
            "youtube", "v3", developerKey=api_key, cache_discovery=False
        )

        search_response = youtube.search().list(
            q=topic,
            part="snippet",
            maxResults=config.DDGS_MAX_RESULTS,
            type="video",
            order="relevance",
        ).execute()

        video_ids = [
            item["id"]["videoId"]
            for item in search_response.get("items", [])
            if item.get("id", {}).get("videoId")
        ]

        if not video_ids:
            return []

        videos_response = youtube.videos().list(
            part="snippet,statistics", id=",".join(video_ids)
        ).execute()

        results = []

        for video in videos_response.get("items", []):
            stats = video.get("statistics", {})
            snippet = video.get("snippet", {})

            def count(key):
                try:
                    return int(stats.get(key, 0))
                except (TypeError, ValueError):
                    return 0

            views = count("viewCount")
            likes = count("likeCount")
            comments = count("commentCount")

            # virality_signals reads `views_per_day` and `engagement_rate`, and
            # this collector never emitted either -- so avg_views_per_day and
            # avg_engagement_rate were hardcoded to 0 by omission, and
            # `momentum` was only ever a rescaled trend_growth. Same defect as
            # the dead `market_report` filter in market_opportunity_signals:
            # a reader and a writer that never agreed on a key name.
            age_days = _age_days(snippet.get("publishedAt", ""))

            results.append({
                "source": "youtube",
                "title": snippet.get("title", ""),
                "url": f"https://youtube.com/watch?v={video['id']}",
                "snippet": snippet.get("description", "")[:500],
                "channel": snippet.get("channelTitle", ""),
                "published": snippet.get("publishedAt", ""),
                "views": views,
                "likes": likes,
                "comments": comments,
                "age_days": age_days,
                "views_per_day": round(views / age_days, 2),
                # Interactions per 100 views. A percentage, so the 0-100 scale
                # the rest of the signal layer uses still applies.
                "engagement_rate": (
                    round((likes + comments) / views * 100, 2) if views else 0.0
                ),
            })

        return results

    except Exception as e:
        print(f"  youtube error: {type(e).__name__}: {str(e)[:150]}")
        return []


class YouTubeCollector:

    async def collect(self, topic: str):
        return await asyncio.to_thread(_fetch, topic)
