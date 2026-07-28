from pydantic import BaseModel


class AnalysisRequest(BaseModel):
    topic: str
