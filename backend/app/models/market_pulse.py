from pydantic import BaseModel

class MarketPulse(BaseModel):
    growth: float
    competition: float
    virality: float
    sentiment: float
    funding: float
    pricing_power: float