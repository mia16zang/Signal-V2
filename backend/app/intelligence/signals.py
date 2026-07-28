from app.models.market_pulse import MarketPulse

def growth_score(evidence):

    growth_keywords = [
        "growth",
        "surge",
        "increase",
        "expansion",
        "demand"
    ]

    score = 0

    for item in evidence:

        text = (
            item["title"] +
            item["snippet"]
        ).lower()

        if any(
            k in text
            for k in growth_keywords
        ):
            score += 10

    return min(score, 100)

def competition_score(evidence):

    keywords = [
        "competitor",
        "alternative",
        "vs",
        "comparison",
        "market leader"
    ]

    score = 0

    for item in evidence:

        text = (
            item["title"] +
            item["snippet"]
        ).lower()

        for keyword in keywords:

            if keyword in text:
                score += 10

    return min(score, 100)

def sentiment_score(evidence):

    positive = [
        "love",
        "great",
        "improved",
        "popular",
        "growth",
        "success"
    ]

    negative = [
        "hate",
        "complaint",
        "issue",
        "problem",
        "expensive",
        "poor"
    ]

    score = 50

    for item in evidence:

        text = (
            item["title"] +
            item["snippet"]
        ).lower()

        for word in positive:
            if word in text:
                score += 5

        for word in negative:
            if word in text:
                score -= 5

    return max(min(score, 100), 0)

def sentiment_score(evidence):

    positive = [
        "love",
        "great",
        "improved",
        "popular",
        "growth",
        "success"
    ]

    negative = [
        "hate",
        "complaint",
        "issue",
        "problem",
        "expensive",
        "poor"
    ]

    score = 50

    for item in evidence:

        text = (
            item["title"] +
            item["snippet"]
        ).lower()

        for word in positive:
            if word in text:
                score += 5

        for word in negative:
            if word in text:
                score -= 5

    return max(min(score, 100), 0)

def funding_score(evidence):

    keywords = [
        "funding",
        "raised",
        "series a",
        "series b",
        "investment",
        "venture capital",
        "seed round"
    ]

    score = 0

    for item in evidence:

        text = (
            item["title"] +
            item["snippet"]
        ).lower()

        for keyword in keywords:

            if keyword in text:
                score += 15

    return min(score, 100)

def pricing_power_score(evidence):

    positive = [
        "premium",
        "subscription",
        "high demand",
        "paid users",
        "revenue growth"
    ]

    negative = [
        "discount",
        "price sensitive",
        "cheap",
        "free alternative"
    ]

    score = 50

    for item in evidence:

        text = (
            item["title"] +
            item["snippet"]
        ).lower()

        for word in positive:
            if word in text:
                score += 5

        for word in negative:
            if word in text:
                score -= 5

    return max(min(score, 100), 0)

def virality_score(evidence):

    keywords = [
        "viral",
        "trending",
        "surge",
        "explosive",
        "popular",
        "rapid growth",
        "growing demand"
    ]

    score = 0

    for item in evidence:

        text = (
            item["title"] +
            item["snippet"]
        ).lower()

        for keyword in keywords:

            if keyword in text:
                score += 15

    return min(score, 100)

def generate_market_pulse(evidence):

    return MarketPulse(
    growth=growth_score(evidence),
    competition=competition_score(evidence),
    virality=virality_score(evidence),
    sentiment=sentiment_score(evidence),
    funding=funding_score(evidence),
    pricing_power=pricing_power_score(evidence)
)

