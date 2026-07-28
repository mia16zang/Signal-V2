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

    @classmethod
    def _key(cls, topic):
        return hashlib.md5(topic.lower().strip().encode()).hexdigest()

    @classmethod
    def _path(cls, topic):
        return cls.CACHE_DIR / f"{cls._key(topic)}.json"

    @classmethod
    def get(cls, topic):
        path = cls._path(topic)

        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            timestamp = datetime.fromisoformat(data["timestamp"])
        except (ValueError, KeyError, OSError) as e:
            # A corrupt or truncated entry should be a miss, not a 500.
            print(f"  cache unreadable ({type(e).__name__}), treating as miss")
            return None

        age = datetime.utcnow() - timestamp
        if age > timedelta(hours=config.CACHE_TTL_HOURS):
            return None

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
