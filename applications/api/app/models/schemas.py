from pydantic import BaseModel, Field
from typing import Optional, List

class DiagnosticRequest(BaseModel):
    symptoms: str
    vin: Optional[str] = None
    error_code: Optional[str] = None
    experiment_id: Optional[str] = None

class ActionItem(BaseModel):
    action: str
    acceptance_criteria: str

class DiagnosticResult(BaseModel):
    diagnosis: str
    confidence_score: float
    supporting_evidence: str
    recommended_actions: List[ActionItem]

class DiagnosticResponse(BaseModel):
    status: int = 200
    provider_used: str
    diagnostic_confidence_score: float
    agent_response_structured: DiagnosticResult
    sources: List[str]
    tracing_metrics: dict

