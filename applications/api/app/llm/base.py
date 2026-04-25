from abc import ABC, abstractmethod

class BaseLLM(ABC):
    """Abstract Base Class (Interface) for all LLM providers"""
    
    @abstractmethod
    async def generate_async(self, prompt: str) -> tuple:
        """Every provider must implement this async method and return (string_answer, token_count, latency_sec)"""
        pass
