from fastapi import (
    APIRouter,
    HTTPException
)

import traceback

from app.models.analysis import (
    AnalysisRequest
)

from app.services.analysis_service import (
    AnalysisService
)

router = APIRouter()

service = AnalysisService()


@router.post("/analyze")
async def analyze(
    request: AnalysisRequest
):

    try:

        return await service.analyze(
            request.topic
        )

    except Exception as e:

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )