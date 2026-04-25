from pydantic import BaseModel
from typing import Optional

class QueryRequest(BaseModel):
    question: str
    vin: str  # We only ask the client for the VIN now!
    prompt_version: Optional[str] = "diagnostic_agent_v2"
    provider: Optional[str] = "SNOWFLAKE"
