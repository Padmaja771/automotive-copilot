import logging
from app.rag.indexer import SnowflakeVectorStore

logger = logging.getLogger("AI_Backend_Retriever")

class RAGRetriever:
    """Business logic for deciding HOW to search the Vector DB"""
    def __init__(self):
        self.vector_store = SnowflakeVectorStore()

    def get_context_for_query(self, question: str, vin: str) -> str:
        logger.info(f"Staging Context Retrieval for VIN: {vin}")
        
        # Here we could implement Re-Ranking, Query Expansion, or filtering
        raw_context = self.vector_store.search_similar_documents(
            semantic_query=question, 
            metadata_filter_vin=vin
        )
        
        return raw_context
