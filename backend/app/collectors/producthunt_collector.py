"""Product Hunt collector. Off by default in PORTFOLIO_MODE.

Two sequential round trips (OAuth token, then GraphQL) for the global "first
50" feed, which is not filtered by topic -- the results are whatever launched
recently, regardless of what was searched. It feeds only
`competitive.launches` and `market.startup_activity`.

`ENABLE_PRODUCT_HUNT=true` restores it. The blocking work now runs on a worker
thread, and the two HTTP calls share one session and carry explicit timeouts
(they previously had none, so a hung Product Hunt could stall the request
indefinitely).
"""

import asyncio
import os
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

TIMEOUT = 8


def _fetch(topic: str):
    client_id = os.getenv("PRODUCTHUNT_CLIENT_ID")
    client_secret = os.getenv("PRODUCTHUNT_CLIENT_SECRET")

    if not (client_id and client_secret):
        print("  producthunt: credentials not set, skipping")
        return []

    query = """
    { posts(first: 50) { edges { node {
        name tagline votesCount commentsCount createdAt url
        topics { edges { node { name } } }
    } } } }
    """

    try:
        with requests.Session() as session:
            token_response = session.post(
                "https://api.producthunt.com/v2/oauth/token",
                json={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "client_credentials",
                },
                timeout=TIMEOUT,
            )
            token_response.raise_for_status()
            token = token_response.json()["access_token"]

            response = session.post(
                "https://api.producthunt.com/v2/api/graphql",
                json={"query": query},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=TIMEOUT,
            )
            response.raise_for_status()

        posts = response.json()["data"]["posts"]["edges"]

        now = datetime.now(timezone.utc)
        results = []

        for post in posts:
            node = post["node"]

            launch_date = node["createdAt"]
            launch_dt = datetime.fromisoformat(launch_date.replace("Z", "+00:00"))
            age_days = max(1, (now - launch_dt).days)

            votes = node["votesCount"]
            comments = node["commentsCount"]

            results.append({
                "source": "producthunt",
                "title": node["name"],
                "url": node["url"],
                "snippet": node["tagline"],
                "votes": votes,
                "comments": comments,
                "launch_date": launch_date,
                "age_days": age_days,
                "votes_per_day": round(votes / age_days, 2),
                "comments_per_day": round(comments / age_days, 2),
                "topics": [
                    t["node"]["name"] for t in node["topics"]["edges"]
                ],
            })

        return results

    except Exception as e:
        print(f"  producthunt error: {type(e).__name__}: {str(e)[:150]}")
        return []


class ProductHuntCollector:

    async def collect(self, topic: str):
        return await asyncio.to_thread(_fetch, topic)
