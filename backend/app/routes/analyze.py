import traceback

from fastapi import APIRouter, HTTPException

from app.models.analysis import AnalysisRequest
from app.services.analysis_service import AnalysisService

router = APIRouter()

service = AnalysisService()

MAX_TOPIC_LENGTH = 120


@router.post("/analyze")
async def analyze(request: AnalysisRequest):
    # An empty topic used to run the full pipeline against queries like
    # " competitors alternatives", burning a real request on nothing.
    topic = (request.topic or "").strip()

    if not topic:
        raise HTTPException(status_code=422, detail="topic is required")

    if len(topic) > MAX_TOPIC_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"topic must be {MAX_TOPIC_LENGTH} characters or fewer",
        )

    try:
        result = await service.analyze(topic)

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    # A briefing the model never wrote is not a briefing.
    #
    # This used to return 200 with the empty contract, which sounds like
    # graceful degradation and is not: `normalise_synthesis` fills the decision
    # with "Monitor" and the confidence with 0, so a provider outage was served
    # to the reader as a considered "Monitor" verdict with the full evidence
    # list rendered underneath it. Measured on 2 of 15 live runs, both caused
    # by a 429 from Gemini.
    #
    # Partial degradation still returns 200 -- a missing section is worth
    # showing with `degraded: true` set. Only a total absence of synthesis
    # becomes an error.
    if result.get("analysis_failed"):
        reason = result.get("degraded_reason") or "the model returned no analysis"
        raise HTTPException(
            status_code=503,
            detail={
                "error": "analysis_unavailable",
                "message": f"Could not produce a briefing for this topic: {reason}.",
                "retryable": True,
                # Present when the provider told us when to come back. The free
                # tier's per-minute limit answers with 33s.
                "retry_after_seconds": result.get("retry_after"),
                "topic": topic,
                # The collection half of the request did succeed, so say so --
                # it explains the wait and tells the caller a retry is cheap.
                "evidence_collected": result.get("meta", {}).get("evidence_count", 0),
            },
        )

    return result
