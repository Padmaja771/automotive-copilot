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

import json
from app.models.schemas import DiagnosticResult

async def execute_ai_query(symptoms: str, vin: str = None, error_code: str = None, experiment_id: str = None, provider: str = "SNOWFLAKE") -> tuple:
    """Core Orchestration: Produces validated Pydantic models from LLM JSON output."""
    logger.info(f"⚡ Executing Diagnostic AI | Experiment: {experiment_id or 'NONE'}")
    
    prompt_version = "diagnostic_expert_json"
    
    if experiment_id:
        config = exp_manager.get_experiment_config(experiment_id)
        if config:
            provider = config.get("llm_provider", provider)
            prompt_version = config.get("prompt_version", prompt_version)

    # 1. RETRIEVER STAGE (Snowflake Hybrid Search)
    retriever = RAGRetriever()
    retrieved_context, retrieval_latency, search_confidence = await retriever.get_context_for_query_async(
        question=f"{symptoms} {error_code or ''}", 
        vin=vin or "GENERAL"
    )
    
    # 2. PROMPT INJECTION STAGE
    template = load_prompt_template(prompt_version)
    final_prompt = template.format(
        context=retrieved_context, 
        symptoms=symptoms, 
        error_code=error_code or "NONE"
    )
    
    # 3. LLM GENERATION STAGE 
    llm = get_llm_provider(provider)
    raw_answer, token_count, llm_latency = await llm.generate_async(final_prompt)
    
    # 💥 STRUCTURED OUTPUT ENFORCEMENT
    # We parse the LLM's string response into a Pydantic model. 
    # If it fails, we have our "Senior Gate" logic here.
    try:
        # If Snowflake Cortex returns a string, we ensure it's valid JSON
        if "[Simulated" in raw_answer:
            # Mock for local dev if no Snowflake connection
            structured_answer = DiagnosticResult(
                diagnosis="Potential Fuel Injector Clog",
                confidence_score=0.85,
                supporting_evidence="Page 12: Misfire symptoms match clogged injectors.",
                recommended_actions=[{"action": "Check pressure", "acceptance_criteria": "45 PSI"}]
            )
        else:
            clean_json = raw_answer.strip().replace("```json", "").replace("```", "")
            structured_answer = DiagnosticResult(**json.loads(clean_json))
            
    except Exception as e:
        logger.error(f"Structured Output Parse Failed: {e}")
        # Return a "Safe Fallback" instead of a 500 error!
        structured_answer = DiagnosticResult(
            diagnosis="Analysis Incomplete",
            confidence_score=0.0,
            supporting_evidence="Could not parse LLM response.",
            recommended_actions=[]
        )
    
    return structured_answer, token_count, retrieval_latency, llm_latency, search_confidence
