"""
Standard 3: AI Accuracy — Cortex Agent Evaluation Tests
Tests the AI diagnostic pipeline for real structured output and confidence SLAs.
"""
import sys
import os
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "applications", "api")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
API_KEY = "super_secret_enterprise_key_2026"
HEADERS = {"x-api-key": API_KEY}

# ─────────────────────────────────────────────
# AI Evaluation Cases (Golden Set)
# ─────────────────────────────────────────────
AI_EVAL_CASES = [
    {
        "id": "AI_EVAL_001",
        "symptoms": "Engine misfiring during cold start, rough idle",
        "error_code": "P0300",
        "vin": "VIN_AWS_001",
        "min_confidence": 0.70,
    },
    {
        "id": "AI_EVAL_002",
        "symptoms": "Coolant temperature warning light on, steam from hood",
        "error_code": "P0217",
        "vin": "VIN_AZURE_002",
        "min_confidence": 0.75,
    },
    {
        "id": "AI_EVAL_003",
        "symptoms": "Oil pressure warning, engine knocking sound",
        "error_code": None,
        "vin": "VIN_AWS_003",
        "min_confidence": 0.65,
    },
]


class TestAIAccuracy:
    """Cortex Agent Evaluation Tests: Validates structured output and confidence SLAs."""

    def test_diagnose_returns_structured_output(self):
        """Every response MUST conform to the DiagnosticResponse Pydantic schema."""
        response = client.post(
            "/api/v1/agent/diagnose",
            json={"symptoms": "Check engine light on", "vin": "VIN_AWS_001"},
            headers=HEADERS,
        )
        assert response.status_code == 200
        data = response.json()

        # ── Structural Assertions ──────────────────────
        assert "agent_response_structured" in data
        structured = data["agent_response_structured"]
        assert "diagnosis" in structured
        assert "confidence_score" in structured
        assert "supporting_evidence" in structured
        assert "recommended_actions" in structured
        assert isinstance(structured["recommended_actions"], list)

    def test_diagnose_confidence_meets_minimum_sla(self):
        """Diagnostic confidence must exceed the 0.65 production floor."""
        response = client.post(
            "/api/v1/agent/diagnose",
            json={"symptoms": "Engine misfiring", "error_code": "P0300", "vin": "VIN_AWS_001"},
            headers=HEADERS,
        )
        assert response.status_code == 200
        conf = response.json()["diagnostic_confidence_score"]
        assert conf >= 0.65, f"Confidence {conf} is below the production SLA of 0.65"

    def test_diagnose_returns_sources(self):
        """RAG responses MUST always return source citations (non-empty list)."""
        response = client.post(
            "/api/v1/agent/diagnose",
            json={"symptoms": "Battery draining overnight", "vin": "VIN_AWS_001"},
            headers=HEADERS,
        )
        assert response.status_code == 200
        sources = response.json()["sources"]
        assert isinstance(sources, list)
        assert len(sources) > 0, "RAG pipeline must always return at least one source."

    def test_diagnose_returns_tracing_metrics(self):
        """Observability: Every response must include latency and token metrics."""
        response = client.post(
            "/api/v1/agent/diagnose",
            json={"symptoms": "Fuel efficiency dropped sharply", "vin": "VIN_AWS_001"},
            headers=HEADERS,
        )
        assert response.status_code == 200
        metrics = response.json()["tracing_metrics"]
        assert "retrieval_time_sec" in metrics
        assert "llm_time_sec" in metrics
        assert "tokens_consumed" in metrics
        assert metrics["tokens_consumed"] > 0

    @pytest.mark.parametrize("case", AI_EVAL_CASES, ids=[c["id"] for c in AI_EVAL_CASES])
    def test_golden_set_confidence_sla(self, case):
        """
        Standard 3: Runs all Golden Set diagnostic cases and asserts confidence SLAs.
        This is equivalent to Cortex Agent Evaluation.
        """
        payload = {"symptoms": case["symptoms"], "vin": case["vin"]}
        if case["error_code"]:
            payload["error_code"] = case["error_code"]

        response = client.post("/api/v1/agent/diagnose", json=payload, headers=HEADERS)
        assert response.status_code == 200

        conf = response.json()["diagnostic_confidence_score"]
        assert conf >= case["min_confidence"], (
            f"[{case['id']}] Confidence {conf:.2f} below SLA {case['min_confidence']}"
        )
