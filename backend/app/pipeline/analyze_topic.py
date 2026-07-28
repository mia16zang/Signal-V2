import time
from datetime import datetime

from app.services.cache_service import (
    CacheService
)

from app.intelligence.intelligence_engine import (
    build_intelligence
)

from app.synthesis.gemini_synthesis import (
    generate_synthesis
)


def analyze_topic(
    topic,
    evidence,
    signals,
    known_competitors=None
):

    cached = CacheService.get(
        topic
    )

    if cached:

        print(
            "\nCACHE HIT\n"
        )

        if "meta" in cached:

            cached["meta"]["cached"] = True

        return cached

    print(
        "\nCACHE MISS\n"
    )

    total_start = time.time()

    intelligence_start = time.time()

    intelligence = build_intelligence(

        topic=topic,

        evidence=evidence,

        signals=signals,

        known_competitors=
        known_competitors
    )

    intelligence_time = round(
        time.time()
        -
        intelligence_start,
        2
    )

    print(
        "\nINTELLIGENCE:",
        intelligence_time,
        "seconds"
    )

    synthesis_start = time.time()

    synthesis = generate_synthesis(

        topic=topic,

        intelligence=intelligence,

        signals=signals
    )

    synthesis_time = round(
        time.time()
        -
        synthesis_start,
        2
    )

    print(
        "\nSYNTHESIS:",
        synthesis_time,
        "seconds"
    )

    total_time = round(
        time.time()
        -
        total_start,
        2
    )

    result = {

        "meta": {

            "topic":
            topic,

            "cached":
            False,

            "generated_at":
            datetime.utcnow().isoformat(),

            "intelligence_time":
            intelligence_time,

            "synthesis_time":
            synthesis_time,

            "total_time":
            total_time
        },

        "signals":
        signals,

        "intelligence":
        intelligence,

        "synthesis":
        synthesis
    }

    CacheService.set(
        topic,
        result
    )

    return result