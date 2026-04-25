from fastapi import APIRouter, Depends, BackgroundTasks
from app.models.schemas import DiagnosticRequest, DiagnosticResponse
from app.core.security import verify_api_key
from app.services.copilot_service import execute_ai_query
from app.core.metrics import record_metric
from app.core.tracing import export_trace
from app.core.experiment_manager import ExperimentManager
import logging

logger = logging.getLogger("AI_Backend_API")
router = APIRouter()
exp_manager = ExperimentManager()

@router.post("/diagnose", response_model=DiagnosticResponse, dependencies=[Depends(verify_api_key)])
async def analyze_vehicle_fault(request: DiagnosticRequest, background_tasks: BackgroundTasks):
    """
    Standard Industry Pattern: AI Diagnostic Engine.
    Inputs: Natural language symptoms + context.
    Outputs: Strict Pydantic-validated JSON.
    """
    logger.info(f"Received Diagnostic Request | VIN: {request.vin or 'Global'}")
    
    # Execute the Core Orchestration
    structured_result, tokens, ret_latency, llm_latency, confidence = await execute_ai_query(
        symptoms=request.symptoms,
        vin=request.vin,
        error_code=request.error_code,
        experiment_id=request.experiment_id
    )
    
    # 💥 ASYNC METRICS & TRACING (Unchanged logic)
    tags = {"experiment": request.experiment_id or "control", "vin": request.vin or "none"}
    background_tasks.add_task(export_trace, request.vin or "none", ret_latency, llm_latency, tokens, "SNOWFLAKE")
    background_tasks.add_task(record_metric, "rag.diagnostic_confidence", confidence, tags)

    return DiagnosticResponse(
        provider_used="SNOWFLAKE",
        diagnostic_confidence_score=confidence,
        agent_response_structured=structured_result,
        sources=["Snowflake Manual Layer", "Diagnostic Log Gold Layer"],
        tracing_metrics={
            "retrieval_time_sec": round(ret_latency, 3),
            "llm_time_sec": round(llm_latency, 3),
            "tokens_consumed": tokens
        }
    )
