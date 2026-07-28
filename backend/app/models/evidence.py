from pydantic import BaseModel

class Evidence(BaseModel):
    source: str
    title: str
    url: str
    snippet: str