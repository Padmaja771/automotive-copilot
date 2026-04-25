import logging
import asyncio

logger = logging.getLogger("AI_Tracing")

async def export_trace(vin: str, retrieval_latency: float, llm_latency: float, total_tokens: int, provider: str):
    """
    Simulates sending an OpenTelemetry trace containing spans for each component 
    of the RAG pipeline asynchronously to an APM backend.
    """
    await asyncio.sleep(1) # simulate networking flush
    logger.info("\n================== OPEN-TELEMETRY TRACE ==================")
    logger.info(f"🔗 Trace Profile | Request: VIN={vin}")
    logger.info(f"   ├─ [Span] Vector DB Retrieval : {retrieval_latency:.3f}s")
    logger.info(f"   ├─ [Span] Core LLM Generation : {llm_latency:.3f}s")
    logger.info(f"   └─ 🎯 Tokens Consumed         : {total_tokens} via {provider}")
    logger.info("==========================================================")
