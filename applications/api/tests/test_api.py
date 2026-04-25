import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_unauthorized_access():
    """Ensure the API blocks unauthenticated RAG queries to protect Snowflake"""
    response = client.post(
        "/api/v1/agent/query", 
        json={
            "question": "What is the engine temp?",
            "vin": "VIN_123"
        }
    )
    # The API should immediately reject the missing headers!
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid Security Key"

def test_authorized_access_with_telemetry():
    """Ensure the RAG orchestrator executes and returns token metrics asynchronously"""
    response = client.post(
        "/api/v1/agent/query", 
        json={
            "question": "What is the engine temp?",
            "vin": "VIN_123",
            "provider": "SNOWFLAKE"
        },
        headers={"x-api-key": "super_secret_enterprise_key_2026"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Assert LLM Abstraction Layer routed correctly
    assert data["provider_used"] == "SNOWFLAKE"
    
    # Assert Observability Metrics are present
    assert "tracing_metrics" in data
    assert "tokens_consumed" in data["tracing_metrics"]
    assert "retrieval_time_sec" in data["tracing_metrics"]
    assert data["tracing_metrics"]["tokens_consumed"] > 0
