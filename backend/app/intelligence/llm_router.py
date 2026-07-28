import os


async def analyze_with_llm(
    evidence
):

    providers = [
        "gemini",
        "groq",
        "keyword"
    ]

    for provider in providers:

        try:

            if provider == "gemini":
                return await analyze_with_gemini(
                    evidence
                )

            if provider == "groq":
                return await analyze_with_groq(
                    evidence
                )

        except Exception as e:

            print(
                f"{provider} failed:",
                str(e)
            )

    from app.intelligence.analysis import (
        analyze_market
    )

    return analyze_market(
        evidence
    )