from pydantic import BaseModel

class Opportunity(BaseModel):
    title: str
    score: float
    confidence: float
    rationale: str