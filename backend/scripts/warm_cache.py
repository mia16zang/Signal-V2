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

# 5 requests/minute means one every 12s. 20s leaves room for the compliance
# retry to fire without tripping the limit.
SPACING_SECONDS = 20


def main():
    topics = sys.argv[1:] or CHIPS
    CacheService.SEED_DIR.mkdir(parents=True, exist_ok=True)

    service = AnalysisService()
    written, failed = [], []

    for index, topic in enumerate(topics, 1):
        print(f"\n=== {index}/{len(topics)}  {topic} ===", flush=True)
        result = asyncio.run(service.analyze(topic))

        # A failed briefing must never become a committed sample.
        if result.get("analysis_failed") or result.get("degraded"):
            print(f"  SKIPPED -- {result.get('degraded_reason')}")
            failed.append(topic)
        else:
            path = CacheService.SEED_DIR / f"{CacheService._key(topic)}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"topic": topic, "result": result}, f,
                          indent=2, ensure_ascii=False)
            size = path.stat().st_size / 1024
            print(f"  wrote {path} ({size:.0f}KB)")
            written.append(topic)

        if index < len(topics):
            time.sleep(SPACING_SECONDS)

    print(f"\n{len(written)} seeds written, {len(failed)} failed")
    for topic in failed:
        print(f"  FAILED: {topic}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
