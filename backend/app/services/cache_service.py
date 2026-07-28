import json
import hashlib
from pathlib import Path
from datetime import datetime
from datetime import timedelta


class CacheService:

    CACHE_DIR = Path(
        "cache"
    )

    CACHE_DIR.mkdir(
        exist_ok=True
    )

    CACHE_TTL_HOURS = 24

    @classmethod
    def _key(
        cls,
        topic
    ):

        return hashlib.md5(
            topic.lower()
            .strip()
            .encode()
        ).hexdigest()

    @classmethod
    def get(
        cls,
        topic
    ):

        key = cls._key(
            topic
        )

        path = (
            cls.CACHE_DIR
            /
            f"{key}.json"
        )

        if not path.exists():

            return None

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        timestamp = datetime.fromisoformat(
            data["timestamp"]
        )

        if (
            datetime.utcnow()
            - timestamp
        ) > timedelta(
            hours=cls.CACHE_TTL_HOURS
        ):

            return None

        return data["result"]

    @classmethod
    def set(
        cls,
        topic,
        result
    ):

        key = cls._key(
            topic
        )

        path = (
            cls.CACHE_DIR
            /
            f"{key}.json"
        )

        payload = {

            "timestamp":
            datetime.utcnow()
            .isoformat(),

            "result":
            result
        }

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                payload,
                f,
                indent=2
            )