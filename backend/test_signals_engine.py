# test_signals.py

from app.signals.signal_engine import (
    build_signals
)

sample_evidence = [
    {
        "source": "google_trends",
        "growth_rate": 18
    },
    {
        "source": "youtube",
        "views_per_day": 4000,
        "engagement_rate": 6.5,
        "comments": 120
    },
    {
        "source": "producthunt",
        "votes_per_day": 85,
        "comments_per_day": 14
    }
]

signals = build_signals(
    sample_evidence
)

print(signals)