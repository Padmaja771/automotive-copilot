from pydantic import BaseModel
from typing import Optional

class QueryRequest(BaseModel):
    question: str
    vin: str  
    prompt_version: Optional[str] = "diagnostic_agent_v2"
    provider: Optional[str] = "SNOWFLAKE"
    experiment_id: Optional[str] = None  # NEW: For A/B Testing and Versioning

