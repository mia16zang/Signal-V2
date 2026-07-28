
from pydantic import BaseModel
from typing import List, Dict, Any

from app.models.evidence import Evidence

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

    market_pulse: Dict[str, Any]

    opportunities: List[Dict[str, Any]]

    threats: List[Dict[str, Any]]

    top_evidence: List[Evidence]