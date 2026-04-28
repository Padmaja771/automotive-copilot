"""
PyTest for applications/api — FastAPI Route Tests
===================================================
Tests the Python files inside applications/api/app/ directly:
  - app/api/routes.py        (endpoint behaviour)
  - app/core/security.py     (authentication guard)
  - app/models/schemas.py    (Pydantic validation)
  - app/services/copilot_service.py (orchestration)
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import DiagnosticResponse, DiagnosticResult, ActionItem

client = TestClient(app)
API_KEY = "super_secret_enterprise_key_2026"
HEADERS = {"x-api-key": API_KEY}

# ── Mock Data for Route Tests ────────────────────────────────────────────────
MOCK_DIAGNOSTIC_RESULT = DiagnosticResult(
    diagnosis="Mocked Diagnosis",
    confidence_score=0.92,
    supporting_evidence="Mocked evidence string",
    recommended_actions=[
        ActionItem(action="Mocked action", acceptance_criteria="Mocked criteria")
    ]
)

MOCK_EXECUTE_RETURN = (MOCK_DIAGNOSTIC_RESULT, 150, 0.1, 0.4, 0.92)

@pytest.fixture(autouse=True)
def mock_copilot_diagnose():
    """Mocks the service layer for all route tests to prevent Snowflake network hangs."""
    with patch("app.api.routes.execute_ai_query", new_callable=AsyncMock, return_value=MOCK_EXECUTE_RETURN):
        yield

# ── Security (tests app/core/security.py) ─────────────────────────────────────

def test_unauthorized_request_returns_401():
    """Ensure the API blocks unauthenticated requests — no x-api-key header."""
    response = client.post(
        "/api/v1/agent/diagnose",
        json={"symptoms": "Engine misfiring", "vin": "VIN_123"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid Security Key"


def test_wrong_api_key_returns_401():
    """Ensure a wrong API key is still rejected (not just missing headers)."""
    response = client.post(
        "/api/v1/agent/diagnose",
        json={"symptoms": "Engine misfiring", "vin": "VIN_123"},
        headers={"x-api-key": "wrong-key-attempt"}
    )
    assert response.status_code == 401


# ── Pydantic Schema Validation (tests app/models/schemas.py) ─────────────────

def test_missing_symptoms_field_returns_422():
    """Pydantic must reject requests that are missing the required `symptoms` field."""
    response = client.post(
        "/api/v1/agent/diagnose",
        json={"vin": "VIN_123"},   # symptoms is missing
        headers=HEADERS
    )
    assert response.status_code == 422


def test_optional_vin_can_be_omitted():
    """VIN is optional — a request without it should still succeed (200)."""
    response = client.post(
        "/api/v1/agent/diagnose",
        json={"symptoms": "Brake pedal feels soft"},
        headers=HEADERS
    )
    assert response.status_code == 200


# ── Route Behaviour (tests app/api/routes.py) ─────────────────────────────────

def test_diagnose_endpoint_exists_and_returns_200():
    """Validates the /diagnose route is registered and live."""
    response = client.post(
        "/api/v1/agent/diagnose",
        json={"symptoms": "Oil pressure warning", "vin": "VIN_AWS_001"},
        headers=HEADERS
    )
    assert response.status_code == 200


def test_response_conforms_to_diagnostic_response_schema():
    """
    Validates that routes.py returns a full DiagnosticResponse structure.
    Tests app/api/routes.py + app/models/schemas.py together.
    """
    response = client.post(
        "/api/v1/agent/diagnose",
        json={"symptoms": "Engine misfiring on cold start", "error_code": "P0300", "vin": "VIN_AWS_001"},
        headers=HEADERS
    )
    assert response.status_code == 200
    data = response.json()

    # Top-level DiagnosticResponse fields
    assert "provider_used" in data
    assert "diagnostic_confidence_score" in data
    assert "agent_response_structured" in data
    assert "sources" in data
    assert "tracing_metrics" in data

    # Nested DiagnosticResult fields
    structured = data["agent_response_structured"]
    assert "diagnosis" in structured
    assert "confidence_score" in structured
    assert "supporting_evidence" in structured
    assert "recommended_actions" in structured
    assert isinstance(structured["recommended_actions"], list)


def test_provider_used_is_snowflake_by_default():
    """Default provider must be SNOWFLAKE — not OpenAI — for zero-egress compliance."""
    response = client.post(
        "/api/v1/agent/diagnose",
        json={"symptoms": "Coolant leak detected"},
        headers=HEADERS
    )
    assert response.status_code == 200
    assert response.json()["provider_used"] == "SNOWFLAKE"


# ── Observability (tests tracing_metrics from the orchestration layer) ─────────

def test_tracing_metrics_are_present_and_non_zero():
    """OpenTelemetry metrics must be returned on every response."""
    response = client.post(
        "/api/v1/agent/diagnose",
        json={"symptoms": "Battery draining overnight", "vin": "VIN_AWS_001"},
        headers=HEADERS
    )
    assert response.status_code == 200
    metrics = response.json()["tracing_metrics"]

    assert "retrieval_time_sec" in metrics
    assert "llm_time_sec" in metrics
    assert "tokens_consumed" in metrics
    assert metrics["tokens_consumed"] > 0


def test_confidence_score_is_between_0_and_1():
    """Diagnostic confidence must always be a valid float between 0.0 and 1.0."""
    response = client.post(
        "/api/v1/agent/diagnose",
        json={"symptoms": "Fuel efficiency dropped", "vin": "VIN_AWS_001"},
        headers=HEADERS
    )
    assert response.status_code == 200
    conf = response.json()["diagnostic_confidence_score"]
    assert 0.0 <= conf <= 1.0, f"Confidence {conf} is outside valid range [0.0, 1.0]"


def test_sources_list_is_non_empty():
    """RAG sources must always be returned — empty sources means no retrieval happened."""
    response = client.post(
        "/api/v1/agent/diagnose",
        json={"symptoms": "ABS warning light on", "vin": "VIN_AWS_001"},
        headers=HEADERS
    )
    assert response.status_code == 200
    sources = response.json()["sources"]
    assert isinstance(sources, list)
    assert len(sources) > 0
