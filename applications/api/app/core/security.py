import logging
from fastapi import Header, HTTPException

logger = logging.getLogger("AI_Backend_Security")

def verify_api_key(x_api_key: str | None = Header(default=None)):
    """API Gateway Security Guardrail"""
    if not x_api_key or x_api_key != "super_secret_enterprise_key_2026":
        logger.warning("🚨 Unauthorized API access attempt blocked!")
        raise HTTPException(status_code=401, detail="Invalid Security Key")
