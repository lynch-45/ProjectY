from typing import List
from pydantic import BaseModel, Field


class SimulationRequest(BaseModel):
    incident_type: str
    asset_id: str
    severity: float = Field(default=1.0, ge=0.1, le=1.0)
    duration: int = Field(default=60, ge=10, le=240)
    interventions: List[str] = []
