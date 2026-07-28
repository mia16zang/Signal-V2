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
        return await service.analyze(topic)

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
