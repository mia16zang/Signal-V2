# app/collectors/google_trends_collector.py

from pytrends.request import TrendReq


class GoogleTrendsCollector:

    async def collect(
        self,
        topic: str
    ):

        try:

            pytrends = TrendReq(
                hl="en-US",
                tz=360
            )

            pytrends.build_payload(
                [topic],
                timeframe="today 12-m"
            )

            data = pytrends.interest_over_time()

            if data.empty:
                return []

            values = data[topic].tolist()

            last_value = values[-1]

            last_30_avg = (
                sum(values[-30:])
                /
                min(30, len(values))
            )

            last_90_avg = (
                sum(values[-90:])
                /
                min(90, len(values))
            )

            growth_rate = round(
                (
                    last_30_avg
                    -
                    last_90_avg
                )
                /
                max(last_90_avg, 1)
                * 100,
                2
            )

            peak = max(values)

            trend = (
                "rising"
                if growth_rate > 0
                else "falling"
            )

            return [
                {
                    "source":
                    "google_trends",

                    "title":
                    topic,

                    "url":
                    "",

                    "snippet":
                    (
                        f"Interest: {last_value}, "
                        f"30d Avg: {last_30_avg:.1f}, "
                        f"90d Avg: {last_90_avg:.1f}, "
                        f"Growth: {growth_rate}%"
                    ),

                    "interest":
                    last_value,

                    "last_30_avg":
                    round(last_30_avg, 1),

                    "last_90_avg":
                    round(last_90_avg, 1),

                    "growth_rate":
                    growth_rate,

                    "peak_interest":
                    peak,

                    "trend":
                    trend
                }
            ]

        except Exception as e:

            print(
                "GOOGLE TRENDS ERROR:",
                e
            )

            return []