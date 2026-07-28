# virality_signals.py

def extract(evidence):

    trend_growth = 0

    total_views_per_day = 0

    total_engagement = 0

    youtube_count = 0

    for item in evidence:

        if item.get("source") =="google_trends":

            trend_growth = item.get(
                "growth_rate",
                0
            )

        if item.get("source") =="youtube":

            youtube_count += 1

            total_views_per_day += item.get(
                "views_per_day",
                0
            )

            total_engagement += item.get(
                "engagement_rate",
                0
            )

    avg_views_per_day = 0
    avg_engagement = 0

    if youtube_count:

        avg_views_per_day = (
            total_views_per_day
            /
            youtube_count
        )

        avg_engagement = (
            total_engagement
            /
            youtube_count
        )

    momentum = min(
        100,
        int(
            (
                trend_growth * 0.5
            )
            +
            (
                avg_engagement * 5
            )
            +
            (
                avg_views_per_day
                / 1000
            )
        )
    )

    return {

        "momentum":
        momentum,

        "trend_growth":
        round(
            trend_growth,
            2
        ),

        "avg_views_per_day":
        round(
            avg_views_per_day,
            2
        ),

        "avg_engagement_rate":
        round(
            avg_engagement,
            2
        )
    }