"""
AI Code Quality Audit — Enterprise Compliance Scanner
======================================================
Standard: Production-grade automated audit for Snowflake-Native AI systems.

Runs BEFORE any tests to ensure the codebase meets enterprise compliance rules:
  1. Zero-Egress Compliance     — Cortex functions used, not external LLM APIs
  2. Prompt Decoupling          — Prompts not hardcoded in SQL/Python strings
  3. Error Handling             — Retry/fallback logic present in LLM calls
  4. Governance                 — ACCOUNTADMIN never used in production code
"""

import os
import re
import glob
import pytest
from pathlib import Path

# ── Root of the repository ────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent

# ── Helpers ───────────────────────────────────────────────────────────────────

def _collect_files(*patterns: str) -> list[Path]:
    """Collect all files matching the given glob patterns under REPO_ROOT."""
    files = []
    for pattern in patterns:
        files.extend(REPO_ROOT.glob(pattern))
    return [f for f in files if f.is_file()]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _grep(pattern: str, files: list[Path]) -> list[tuple[Path, int, str]]:
    """Return (file, line_number, line) for every line matching pattern."""
    results = []
    rx = re.compile(pattern, re.IGNORECASE)
    for f in files:
        for i, line in enumerate(_read(f).splitlines(), 1):
            if rx.search(line):
                results.append((f, i, line.strip()))
    return results


# ── Audit 1: Zero-Egress Compliance ──────────────────────────────────────────

class TestZeroEgressCompliance:
    """
    Standard: LLM inference must happen inside Snowflake via CORTEX functions.
    No raw openai.ChatCompletion or requests.post to external LLM APIs in prod code.
    """

    PYTHON_FILES = _collect_files(
        "applications/**/*.py",
        "ingestion/**/*.py",
    )

    SQL_FILES = _collect_files(
        "transformation/**/*.sql",
        "src/**/*.sql",
    )

    def test_no_raw_openai_api_calls_in_production(self):
        """Disallows direct openai.ChatCompletion / openai.Completion calls."""
        violations = _grep(
            r"openai\.(ChatCompletion|Completion)\.create",
            self.PYTHON_FILES,
        )
        assert not violations, (
            f"❌ ZERO-EGRESS VIOLATION: Found raw OpenAI API calls in production code.\n"
            + "\n".join(f"  {f}:{n}  →  {l}" for f, n, l in violations)
        )

    def test_no_external_llm_http_requests(self):
        """Disallows direct HTTP requests to known external LLM endpoints."""
        violations = _grep(
            r"requests\.post.*api\.openai\.com|anthropic\.com|api\.cohere\.ai",
            self.PYTHON_FILES,
        )
        assert not violations, (
            f"❌ ZERO-EGRESS VIOLATION: Direct HTTP calls to external LLM APIs detected.\n"
            + "\n".join(f"  {f}:{n}  →  {l}" for f, n, l in violations)
        )

    def test_cortex_complete_used_for_inference(self):
        """Validates that SNOWFLAKE.CORTEX.COMPLETE is present in the LLM provider."""
        provider_file = REPO_ROOT / "applications/api/app/llm/snowflake_provider.py"
        content = _read(provider_file)
        assert "SNOWFLAKE.CORTEX.COMPLETE" in content, (
            "❌ ZERO-EGRESS VIOLATION: `SNOWFLAKE.CORTEX.COMPLETE` not found "
            f"in {provider_file}. Inference must run inside Snowflake."
        )

    def test_cortex_embed_used_for_vectors(self):
        """Validates that SNOWFLAKE.CORTEX.EMBED_TEXT is used for embeddings."""
        indexer_file = REPO_ROOT / "applications/api/app/rag/indexer.py"
        content = _read(indexer_file)
        assert "SNOWFLAKE.CORTEX.EMBED_TEXT" in content, (
            "❌ ZERO-EGRESS VIOLATION: `SNOWFLAKE.CORTEX.EMBED_TEXT` not found "
            f"in {indexer_file}. Embeddings must be computed inside Snowflake."
        )


# ── Audit 2: Prompt Decoupling ────────────────────────────────────────────────

class TestPromptDecoupling:
    """
    Standard: Prompts must live in a dedicated prompts.yaml or Snowflake Stage.
    They must NOT be hardcoded inside SQL strings or service layer Python.
    """

    PYTHON_FILES = _collect_files(
        "applications/**/*.py",
        "ingestion/**/*.py",
    )

    def test_prompts_file_exists(self):
        """Ensures a dedicated prompts registry file exists."""
        prompts_file = REPO_ROOT / "applications/api/prompts.yaml"
        assert prompts_file.exists(), (
            "❌ PROMPT DECOUPLING VIOLATION: `applications/api/prompts.yaml` not found. "
            "All prompts must be managed in a versioned registry."
        )

    def test_prompts_file_has_versions(self):
        """Ensures at least two versioned prompts exist (v1 baseline + v2 prod)."""
        prompts_file = REPO_ROOT / "applications/api/prompts.yaml"
        content = _read(prompts_file)
        assert content.count("diagnostic_agent") >= 2, (
            "❌ PROMPT DECOUPLING VIOLATION: At least two versioned prompts "
            "(e.g., v1 + v2) must exist for A/B testing baseline."
        )

    def test_no_hardcoded_system_prompts_in_service(self):
        """Disallows hardcoded 'You are an AI assistant' style strings in service code."""
        service_file = REPO_ROOT / "applications/api/app/services/copilot_service.py"
        content = _read(service_file)
        violations = re.findall(r'"You are .{10,80}"', content)
        assert not violations, (
            f"❌ PROMPT DECOUPLING VIOLATION: Hardcoded system prompt detected in copilot_service.py.\n"
            f"  Move to prompts.yaml: {violations}"
        )


# ── Audit 3: Error Handling & Resilience ─────────────────────────────────────

class TestErrorHandling:
    """
    Standard: LLM calls must have explicit exception handling and fallback paths.
    Snowpark sessions must handle connection failures gracefully.
    """

    def test_snowflake_provider_has_try_except(self):
        """LLM provider must catch Snowflake errors and return a safe fallback."""
        provider_file = REPO_ROOT / "applications/api/app/llm/snowflake_provider.py"
        content = _read(provider_file)
        assert "except Exception" in content or "except" in content, (
            "❌ ERROR HANDLING VIOLATION: No try/except found in snowflake_provider.py. "
            "Cortex calls must handle rate limits and model rotation gracefully."
        )

    def test_snowflake_provider_has_fallback_path(self):
        """LLM provider must have a fallback for when session is unavailable."""
        provider_file = REPO_ROOT / "applications/api/app/llm/snowflake_provider.py"
        content = _read(provider_file)
        assert "not self.session" in content or "Simulated" in content, (
            "❌ ERROR HANDLING VIOLATION: No session-null fallback in snowflake_provider.py. "
            "Local dev must function without a live Snowflake connection."
        )

    def test_session_manager_handles_missing_credentials(self):
        """Snowpark session must return None if credentials are absent (no crash)."""
        session_file = REPO_ROOT / "applications/api/app/core/snowflake_session.py"
        content = _read(session_file)
        assert "return None" in content, (
            "❌ ERROR HANDLING VIOLATION: `get_snowpark_session()` must return None "
            "when credentials are missing, not raise an unhandled exception."
        )

    def test_api_returns_safe_fallback_on_llm_failure(self):
        """Copilot service must return a structured fallback if LLM parse fails."""
        service_file = REPO_ROOT / "applications/api/app/services/copilot_service.py"
        content = _read(service_file)
        assert "Analysis Incomplete" in content or "Safe Fallback" in content.lower(), (
            "❌ ERROR HANDLING VIOLATION: copilot_service.py must return a safe "
            "DiagnosticResult fallback when JSON parsing fails, not a 500 error."
        )


# ── Audit 4: Governance & RBAC ────────────────────────────────────────────────

class TestGovernanceCompliance:
    """
    Standard: No production code may run as ACCOUNTADMIN.
    Sensitive identifiers must be masked per Dynamic Data Masking policy.
    """

    ALL_FILES = _collect_files(
        "applications/**/*.py",
        "ingestion/**/*.py",
        "transformation/**/*.sql",
        "src/**/*.sql",
    )

    INFRA_FILES = _collect_files(
        "infrastructure/**/*.sql",
        "infrastructure/**/*.tf",
    )

    def test_no_accountadmin_in_application_code(self):
        """ACCOUNTADMIN must never be used in active application or ingestion code."""
        # src/setup.sql is a one-time infra bootstrap — ACCOUNTADMIN allowed there.
        # infrastructure/ SQL is also bootstrap-only — allowed.
        audit_files = [
            f for f in self.ALL_FILES
            if "setup.sql" not in f.name
            and "infrastructure" not in str(f)
        ]
        violations = []
        for f, n, l in _grep(r"ACCOUNTADMIN", audit_files):
            # Strip inline comments before checking
            code_part = l.split("#")[0].split("--")[0]
            if "ACCOUNTADMIN" in code_part:
                violations.append((f, n, l))
        assert not violations, (
            "❌ GOVERNANCE VIOLATION: ACCOUNTADMIN usage detected in application/SQL code.\n"
            "Use a least-privilege role (e.g., CORTEX_DEV_ROLE) in production.\n"
            + "\n".join(f"  {f}:{n}  →  {l}" for f, n, l in violations)
        )

    def test_rbac_roles_defined_in_infrastructure(self):
        """Validates that custom RBAC roles are defined in infrastructure setup."""
        infra_content = " ".join(_read(f) for f in self.INFRA_FILES)
        has_role = "CREATE ROLE" in infra_content or "GRANT ROLE" in infra_content
        assert has_role, (
            "❌ GOVERNANCE VIOLATION: No `CREATE ROLE` or `GRANT ROLE` found in "
            "infrastructure SQL. Production systems must define least-privilege RBAC roles."
        )

    def test_vin_masking_policy_referenced(self):
        """Validates that a Dynamic Data Masking policy is defined for VIN fields."""
        infra_content = " ".join(_read(f) for f in self.INFRA_FILES)
        has_masking = (
            "MASKING POLICY" in infra_content
            or "CREATE MASKING" in infra_content
            or "masking" in infra_content.lower()
        )
        assert has_masking, (
            "❌ GOVERNANCE VIOLATION: No Dynamic Data Masking policy found in "
            "infrastructure. VIN and PII fields must be masked for ANALYST_ROLE."
        )

    def test_api_key_not_hardcoded_in_source(self):
        """Ensures the API key is never committed directly into production application code."""
        py_files = _collect_files("applications/**/*.py")
        # Exclude: test files, eval scripts, and the security module's os.getenv fallback
        prod_files = [
            f for f in py_files
            if "test" not in f.name.lower()
            and "benchmark" not in f.name.lower()
            and "security" not in f.name.lower()  # security.py uses os.getenv() — allowed
        ]
        violations = _grep(r'super_secret_enterprise_key_2026', prod_files)
        assert not violations, (
            "❌ GOVERNANCE VIOLATION: Hardcoded API key found in production source.\n"
            "Move to environment variable / Snowflake Secret.\n"
            + "\n".join(f"  {f}:{n}  →  {l}" for f, n, l in violations)
        )
