import os
import yaml
import logging
from app.llm.snowflake_provider import LLMProvider
from app.rag.retriever import RAGRetriever

logger = logging.getLogger("AI_Backend_Service")

def load_prompt_template(version_key: str) -> str:
    # Points to applications/api/prompts.yaml
    prompts_path = os.path.join(os.path.dirname(__file__), "..", "..", "prompts.yaml")
    try:
        with open(prompts_path, 'r') as file:
            data = yaml.safe_load(file)
        return data.get("prompts", {}).get(version_key, "Answer the question: {question}")
    except Exception as e:
        logger.error(f"Failed to load prompts mapping: {e}")
        return "Answer the question: {question}"

def execute_ai_query(question: str, vin: str, prompt_version: str, provider: str) -> str:
    """Core Orchestration: Client -> Retriever -> VectorDB -> Prompt -> LLM"""
    logger.info("⚡ Initializing RAG Pipeline Flow...")
    
    # 1. RETRIEVER STAGE (Query the Vector DB)
    retriever = RAGRetriever()
    retrieved_context = retriever.get_context_for_query(question=question, vin=vin)
    
    # 2. PROMPT INJECTION STAGE
    template = load_prompt_template(prompt_version)
    final_prompt = template.format(context=retrieved_context, question=question)
    
    # 3. LLM GENERATION STAGE
    llm = LLMProvider(provider=provider)
    return llm.generate(final_prompt)
