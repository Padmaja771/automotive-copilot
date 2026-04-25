from fastapi import APIRouter, Depends
from app.models.schemas import QueryRequest
from app.core.security import verify_api_key
from app.services.copilot_service import execute_ai_query
import logging

logger = logging.getLogger("AI_Backend_API")
router = APIRouter()

@router.post("/query", dependencies=[Depends(verify_api_key)])
async def query_ai_agent(request: QueryRequest):
    """Secure REST endpoint executing the dynamic AI RAG workflow."""
    logger.info(f"Received Incoming API Request | Target VIN: {request.vin}")
    
    answer = execute_ai_query(
        question=request.question,
        vin=request.vin,
        prompt_version=request.prompt_version,
        provider=request.provider
    )
    
    return {
        "status": 200,
        "provider_used": request.provider,
        "prompt_version": request.prompt_version,
        "agent_response": answer
    }
