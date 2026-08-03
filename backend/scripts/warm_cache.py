"""Regenerate the checked-in sample briefings for the landing-page suggestions.

These are committed, unlike `cache/`, so a fresh deploy serves the four topics
a visitor is most likely to click without calling the provider at all.

Run when the payload shape changes or the samples get stale:

    python scripts/warm_cache.py
    python scripts/warm_cache.py "Some other topic"

Calls are spaced because the free tier allows 5 requests per minute per model.
"""

import asyncio
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Always regenerate: reading a stale entry back and writing it out again would
# defeat the point of the script.
os.environ["CACHE_ENABLED"] = "false"

from app.services.analysis_service import AnalysisService  # noqa: E402
from app.services.cache_service import CacheService  # noqa: E402

# The four suggestions on the landing page. Keep in step with the frontend.
CHIPS = [
    "AI note-taking for clinicians",
    "Carbon accounting for SMBs",
    "Developer tools for edge functions",
    "Vertical CRM for law firms",
]

# One topic at a time, with the window given time to clear between them.
#
# 5 requests/minute sounds like one every 12s, and 20s was the first guess.
# It failed on 3 of 4 topics: an analysis takes 30-80s, so the calls were
# already 50-100s apart and still hit the limit. The deployed service shares
# the same key, so anything else touching /analyze -- a visitor, a browser tab
# left open -- competes for the same bucket. Waiting a clear two minutes is the
# difference between a run that works and a run that wastes four minutes.
SPACING_SECONDS = 120

# Per topic, not per run. A rate limit is transient, so the topic is retried
# rather than abandoned.
MAX_ATTEMPTS = 4


def capture(service, topic):
    """Analyse one topic, retrying while the provider is merely rate limited.

    Returns a clean result or None. Never returns a degraded one -- a briefing
    written by the fallback model, or missing sections, must not become a
    committed sample that ships to every visitor.
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        result = asyncio.run(service.analyze(topic))

        if not (result.get("analysis_failed") or result.get("degraded")):
            return result

        reason = result.get("degraded_reason") or "unknown"
        # The provider says when it will accept another request; believe it
        # rather than guessing, and add headroom.
        wait = (result.get("retry_after") or 45) + 20

        if attempt == MAX_ATTEMPTS:
            print(f"  giving up after {attempt} attempts -- {reason}", flush=True)
            return None

        print(f"  attempt {attempt} unusable ({reason}); "
              f"retrying in {wait:.0f}s", flush=True)
        time.sleep(wait)

    return None


def main():
    topics = sys.argv[1:] or CHIPS
    CacheService.SEED_DIR.mkdir(parents=True, exist_ok=True)

    service = AnalysisService()
    written, failed = [], []

    for index, topic in enumerate(topics, 1):
        print(f"\n=== {index}/{len(topics)}  {topic} ===", flush=True)
        result = capture(service, topic)

        if result is None:
            failed.append(topic)
        else:
            path = CacheService.SEED_DIR / f"{CacheService._key(topic)}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"topic": topic, "result": result}, f,
                          indent=2, ensure_ascii=False)
            size = path.stat().st_size / 1024
            print(f"  wrote {path.name} ({size:.0f}KB)", flush=True)
            written.append(topic)

        if index < len(topics):
            print(f"  pausing {SPACING_SECONDS}s before the next topic",
                  flush=True)
            time.sleep(SPACING_SECONDS)

    print(f"\n{len(written)} seeds written, {len(failed)} failed")
    for topic in failed:
        print(f"  FAILED: {topic}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
