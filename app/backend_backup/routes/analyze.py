from fastapi import APIRouter

from app.models.analysis import (
    AnalysisRequest,
    AnalysisResponse
)

from app.services.analysis_service import (
    AnalysisService
)

router = APIRouter()

service = AnalysisService()


@router.post(
    "/analyze",
    response_model=AnalysisResponse
)
async def analyze(
    request: AnalysisRequest
):

    result = await service.analyze(
        request.topic
    )

    return result