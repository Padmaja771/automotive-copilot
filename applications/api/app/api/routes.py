from fastapi import APIRouter, Depends, BackgroundTasks
from app.models.schemas import QueryRequest
from app.core.security import verify_api_key
from app.services.copilot_service import execute_ai_query
from app.core.metrics import record_metric
from app.core.tracing import export_trace
from app.core.experiment_manager import ExperimentManager
import logging

logger = logging.getLogger("AI_Backend_API")
router = APIRouter()
exp_manager = ExperimentManager()

@router.post("/query", dependencies=[Depends(verify_api_key)])
async def query_ai_agent(request: QueryRequest, background_tasks: BackgroundTasks):
    """Secure REST endpoint executing the dynamic AI RAG workflow."""
    logger.info(f"Received Incoming API Request | Target VIN: {request.vin} | Experiment: {request.experiment_id}")
    
    answer, tokens, ret_latency, llm_latency, confidence = await execute_ai_query(
        question=request.question,
        vin=request.vin,
        prompt_version=request.prompt_version,
        provider=request.provider,
        experiment_id=request.experiment_id
    )
    
    # 💥 ASYNC TRACES: Send beautiful Span profiles to OpenTelemetry
    background_tasks.add_task(export_trace, request.vin, ret_latency, llm_latency, tokens, request.provider)
    
    # 📈 ASYNC METRICS: Push raw float/int gauges to Prometheus
    tags = {"provider": request.provider, "vin": request.vin, "experiment": request.experiment_id or "control"}
    background_tasks.add_task(record_metric, "rag.span.retrieval_sec", ret_latency, tags)
    background_tasks.add_task(record_metric, "rag.span.generation_sec", llm_latency, tags)
    background_tasks.add_task(record_metric, "rag.token_usage.sum", tokens, tags)
    background_tasks.add_task(record_metric, "rag.diagnostic_confidence", confidence, tags)

    # 🧪 EXPERIMENT LOGGING: If in an experiment, log the run for later analysis (MLflow style)
    if request.experiment_id:
        background_tasks.add_task(exp_manager.log_run, request.experiment_id, request.vin, {
            "tokens": tokens,
            "latency_total": ret_latency + llm_latency,
            "confidence": confidence
        })
    
    return {
        "status": 200,
        "provider_used": request.provider,
        "diagnostic_confidence_score": round(confidence, 3),
        "agent_response": answer,
        "tracing_metrics": {
            "retrieval_time_sec": round(ret_latency, 3),
            "llm_time_sec": round(llm_latency, 3),
            "tokens_consumed": tokens
        }
    }
