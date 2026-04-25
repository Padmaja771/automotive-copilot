import logging
from fastapi import FastAPI
from app.api.routes import router

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')

app = FastAPI(title="Automotive Copilot Enterprise API", version="2.0.0")

# Register modular routes!
app.include_router(router, prefix="/api/v1/agent", tags=["AI Agent"])
