"""Google Trends collector. Off by default in PORTFOLIO_MODE.

Measured against the live endpoint: 7.4s to an HTTP 429, returning zero
evidence. pytrends 4.9.2 is rate limited from essentially any cloud IP, so in
the deployed demo this contributed latency and nothing else. It stays in the
tree, and `ENABLE_GOOGLE_TRENDS=true` turns it back on.

As with the other collectors, the blocking work now runs on a worker thread.
"""

import asyncio

from pytrends.request import TrendReq


def _fetch(topic: str):
    try:
        pytrends = TrendReq(hl="en-US", tz=360)
        pytrends.build_payload([topic], timeframe="today 12-m")
        data = pytrends.interest_over_time()

        if data.empty:
            return []

        values = data[topic].tolist()
        last_value = values[-1]
        last_30_avg = sum(values[-30:]) / min(30, len(values))
        last_90_avg = sum(values[-90:]) / min(90, len(values))

        growth_rate = round(
            (last_30_avg - last_90_avg) / max(last_90_avg, 1) * 100, 2
        )

        return [{
            "source": "google_trends",
            "title": topic,
            "url": "",
            "snippet": (
                f"Interest: {last_value}, "
                f"30d Avg: {last_30_avg:.1f}, "
                f"90d Avg: {last_90_avg:.1f}, "
                f"Growth: {growth_rate}%"
            ),
            "interest": last_value,
            "last_30_avg": round(last_30_avg, 1),
            "last_90_avg": round(last_90_avg, 1),
            "growth_rate": growth_rate,
            "peak_interest": max(values),
            "trend": "rising" if growth_rate > 0 else "falling",
        }]

    except Exception as e:
        print(f"  google trends error: {type(e).__name__}: {str(e)[:150]}")
        return []


class GoogleTrendsCollector:

    async def collect(self, topic: str):
        return await asyncio.to_thread(_fetch, topic)
