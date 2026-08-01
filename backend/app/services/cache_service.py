"""Filesystem cache, keyed on the normalised topic.

Unchanged in shape and on-disk format -- the 14 responses already in
`backend/cache/` still load. What changed is that AnalysisService now
consults it before collection rather than after, and writes are atomic so an
interrupted request cannot leave a half-written file that poisons the topic.
"""

import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from app import config


class CacheService:

    CACHE_DIR = Path("cache")
    CACHE_DIR.mkdir(exist_ok=True)

    # Committed sample briefings for the landing-page suggestions.
    #
    # `cache/` is gitignored and expires after CACHE_TTL_HOURS, so warming it
    # locally does nothing for a deployment -- Render boots with an empty
    # directory every time. These are checked in instead, and are not subject
    # to the TTL, so the four topics a visitor is most likely to click never
    # reach the provider at all.
    #
    # That matters because the free tier allows 5 requests per minute per
    # model (measured: quotaId GenerateRequestsPerMinutePerProjectPerModel-
    # FreeTier, quotaValue 5). Two people clicking the same suggestion at once
    # was enough to produce a 503.
    SEED_DIR = Path("fixtures/seed")

    @classmethod
    def _key(cls, topic):
        return hashlib.md5(topic.lower().strip().encode()).hexdigest()

    @classmethod
    def _path(cls, topic):
        return cls.CACHE_DIR / f"{cls._key(topic)}.json"

    @classmethod
    def _seed_path(cls, topic):
        return cls.SEED_DIR / f"{cls._key(topic)}.json"

    @classmethod
    def _seed(cls, topic):
        """A checked-in sample, if one exists for this topic.

        No TTL. An expiring seed would silently start calling the provider
        again a day after deploy, which is the failure this is meant to remove.
        """
        path = cls._seed_path(topic)
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (ValueError, OSError) as e:
            print(f"  seed unreadable ({type(e).__name__}), treating as miss")
            return None

        result = data.get("result")
        if not isinstance(result, dict):
            return None

        # Say what it is. `generated_at` keeps the real capture time, so the
        # response never claims to be fresher than it is.
        result.setdefault("meta", {})["seeded"] = True
        return result

    @classmethod
    def get(cls, topic):
        path = cls._path(topic)

        # A live entry always wins: it is fresher than the checked-in sample,
        # and a topic re-run since deploy should serve what it produced.
        if not path.exists():
            return cls._seed(topic)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            timestamp = datetime.fromisoformat(data["timestamp"])
        except (ValueError, KeyError, OSError) as e:
            # A corrupt or truncated entry should be a miss, not a 500.
            print(f"  cache unreadable ({type(e).__name__}), treating as miss")
            return cls._seed(topic)

        age = datetime.utcnow() - timestamp
        if age > timedelta(hours=config.CACHE_TTL_HOURS):
            return cls._seed(topic)

        return data["result"]

    @classmethod
    def set(cls, topic, result):
        path = cls._path(topic)
        tmp = path.with_suffix(".tmp")

        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "result": result,
        }

        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp, path)
        except OSError as e:
            print(f"  cache write failed ({type(e).__name__}), continuing")
            tmp.unlink(missing_ok=True)
