"""YouTube collector.

`collect` was `async def` wrapping entirely synchronous googleapiclient work,
so awaiting it blocked the event loop for its full duration -- which meant the
concurrent DDGS searches could not make progress while it ran. The blocking
work now happens on a worker thread and only the wrapper is async.
"""

import asyncio
import os

from dotenv import load_dotenv
from googleapiclient.discovery import build

from app import config

load_dotenv()


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

            results.append({
                "source": "youtube",
                "title": snippet.get("title", ""),
                "url": f"https://youtube.com/watch?v={video['id']}",
                "snippet": snippet.get("description", "")[:500],
                "channel": snippet.get("channelTitle", ""),
                "published": snippet.get("publishedAt", ""),
                "views": count("viewCount"),
                "likes": count("likeCount"),
                "comments": count("commentCount"),
            })

        return results

    except Exception as e:
        print(f"  youtube error: {type(e).__name__}: {str(e)[:150]}")
        return []


class YouTubeCollector:

    async def collect(self, topic: str):
        return await asyncio.to_thread(_fetch, topic)
