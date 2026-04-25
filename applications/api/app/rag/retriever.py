import logging
import asyncio
from app.rag.indexer import SnowflakeVectorStore

logger = logging.getLogger("AI_Backend_Retriever")

class RAGRetriever:
    """Business logic for deciding HOW to search the Vector DB"""
    def __init__(self):
        self.vector_store = SnowflakeVectorStore()

    async def get_context_for_query_async(self, question: str, vin: str) -> tuple:
        import time
        logger.info(f"Staging Asynchronous Hybrid Context Retrieval for VIN: {vin}")
        
        start_time = time.time()
        # Simulating external Latency to the DB
        await asyncio.sleep(0.4)
        
        raw_context, confidence_score = self.vector_store.hybrid_search(
            semantic_query=question, 
            metadata_filter_vin=vin
        )
        
        retrieval_latency = time.time() - start_time
        return raw_context, retrieval_latency, confidence_score
