import os
import yaml
import logging
from app.llm.snowflake_provider import SnowflakeProvider
from app.llm.openai_provider import OpenAIProvider
from app.rag.retriever import RAGRetriever
from app.core.experiment_manager import ExperimentManager

logger = logging.getLogger("AI_Backend_Service")
exp_manager = ExperimentManager()

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

def get_llm_provider(provider_name: str):
    """Factory Pattern: Instantiates the selected LLM Provider securely!"""
    if provider_name.upper() == "OPENAI":
        return OpenAIProvider()
    return SnowflakeProvider()

async def execute_ai_query(question: str, vin: str, prompt_version: str, provider: str, experiment_id: str = None) -> tuple:
    """Core Orchestration: Asynchronous Client -> Retriever -> Snowflake Search -> Prompt -> LLM"""
    logger.info(f"⚡ Executing Query | Experiment: {experiment_id or 'NONE'}")
    
    if experiment_id:
        config = exp_manager.get_experiment_config(experiment_id)
        if config:
            provider = config.get("llm_provider", provider)
            prompt_version = config.get("prompt_version", prompt_version)
            logger.info(f"📈 Experiment {experiment_id} applied: Using {provider} + {prompt_version}")

    # 1. RETRIEVER STAGE (Use Snowflake Hybrid Search Asynchronously)
    retriever = RAGRetriever()
    retrieved_context, retrieval_latency, confidence = await retriever.get_context_for_query_async(question=question, vin=vin)
    
    # 2. PROMPT INJECTION STAGE
    template = load_prompt_template(prompt_version)
    final_prompt = template.format(context=retrieved_context, question=question)
    
    # 3. LLM GENERATION STAGE 
    llm = get_llm_provider(provider)
    answer, token_count, llm_latency = await llm.generate_async(final_prompt)
    
    return answer, token_count, retrieval_latency, llm_latency, confidence
