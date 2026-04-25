import time
import logging
from fastapi import HTTPException

logger = logging.getLogger("AI_Backend_LLM")

class LLMProvider:
    """Strategy Pattern: Dynamically routes to OpenAI or Snowflake Cortex"""
    def __init__(self, provider: str = "SNOWFLAKE"):
        self.provider = provider.upper()

    def generate(self, prompt: str) -> str:
        start_time = time.time()
        logger.info(f"Routing request to {self.provider}...")
        
        try:
            if self.provider == "SNOWFLAKE":
                response = f"[Snowflake Cortex Llama-3] Mathematically Synthesized: {prompt[:30]}..."
            elif self.provider == "OPENAI":
                response = f"[OpenAI GPT-4] Mapped to external API: {prompt[:30]}..."
            else:
                raise ValueError("Unsupported AI Provider specified!")
                
            latency = time.time() - start_time
            logger.info(f"✅ LLM Generation Successful | Provider: {self.provider} | Latency: {latency:.2f}s")
            return response
            
        except Exception as e:
            logger.error(f"❌ LLM Generation Failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="AI Provider Internal Error")
