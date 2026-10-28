from typing import Optional
from pydantic import BaseModel, Field

class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = ""
    service: str = Field(min_length=1, max_length=100)
    severity: str = Field(default="warning", pattern="^(critical|warning|info)$")
    error_message: str = ""
    logs: list[dict] = []
    metrics: list[dict] = []
    events: list[dict] = []

class MetricsIn(BaseModel):
    metrics: list[dict] = Field(min_length=1)

class ResolveIn(BaseModel):
    notes: str = Field(min_length=1, max_length=2000)

class LivePoint(BaseModel):
    buffer: list[dict]
    service: Optional[str] = "api-gateway"
