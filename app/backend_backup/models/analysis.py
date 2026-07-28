from pydantic import BaseModel
from typing import List


class Evidence(BaseModel):
    source: str
    title: str
    url: str
    snippet: str


class AnalysisRequest(BaseModel):
    topic: str


class AnalysisResponse(BaseModel):
    topic: str
    evidence_count: int
    evidence: List[Evidence]