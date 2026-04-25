# ❄️ Automotive Intelligence Copilot: Enterprise AI Pipeline

A production-grade, Snowflake-native AI system designed for the Automotive sector. This project demonstrates a complete lifecycle from Multi-Cloud data ingestion to semantic AI inference with integrated data governance.

## 🏗️ 2026 Core Architecture

This project strictly adheres to "Snowflake-Native" principles, ensuring data never leaves the governed perimeter.

### 🌓 1. Data Ingestion & Orchestration (Snowpark)
*   **Role:** Programmatic ETL and Pipeline Orchestration.
*   **Implementation:** Located in `ingestion/snowpark_ingestion.py`.
*   **Why:** Snowpark provides the Python-native flexibility required for complex JSON parsing from AWS/Azure streams and handling real-time unstructured data ingestion.

### 💎 2. Transformation Layer (dbt Medallion)
*   **Role:** Declarative SQL Transformation and Data Modeling.
*   **Implementation:** Located in `transformation/dbt_project/`.
*   **Layers:** 
    *   **Bronze:** Raw landing zone for telemetry.
    *   **Silver:** Cleaned, deduplicated, and standardized diagnostic data.
    *   **Gold:** High-value business facts and aggregated dealership error reporting.

### 🔍 3. Semantic Retrieval Layer (Snowflake Vector Search)
*   **Precision Note:** This project utilizes Snowflake's **Native Vector Support** (not an external Vector DB).
*   **Features:**
    *   **Hybrid Search:** Combined BM25 keyword lookup and Dense Vector similarity.
    *   **Reranking:** Integrated Reciprocal Rank Fusion (RRF) for diagnostic fault prioritization.
    *   **Compute:** Retrieval executes via `VECTOR_L2_DISTANCE` within Snowflake's compute engine.

### 🤖 4. AI Inference Layer (Snowflake Cortex)
*   **Implementation:** `applications/api/app/llm/snowflake_provider.py`.
*   **Features:** Executes `SNOWFLAKE.CORTEX.COMPLETE` using `mistral-large2` for secure, zero-egress LLM synthesis.

### 🛡️ 5. Data Governance & Security
*   **Implementation:** `infrastructure/snowflake/governance/06_data_masking.sql`.
*   **Signals:**
    *   **Dynamic Data Masking:** Critical fields like `VIN` are dynamically obfuscated based on RBAC roles.
    *   **Object Tagging:** Sensitive data is tagged with Privacy Level tags for SOC2 audit compliance.
    *   **RBAC (Role-Based Access Control):** Granular separation between `CORTEX_DEV_ROLE` and `ANALYST_ROLE`.

## 🛠️ Developer Operations (DevOps)
*   **CI/CD:** Automated `.github/workflows/ci_cd_pipeline.yml` for infrastructure and dbt validation.
*   **Observability:** Integrated OpenTelemetry tracing and Prometheus metrics in the backend for RAG latency tracking.
*   **Testing:** Comprehensive `pytest` suite for API security and AI benchmark evaluations.

## 🚀 Getting Started

1.  **Configure Environment:** Populate `.env` with Snowflake credentials.
2.  **Deploy Infrastructure:** `terraform apply` within the infrastructure folder.
3.  **Run Ingestion:** `python ingestion/snowpark_ingestion.py`.
4.  **Launch AI Gateway:**
    ```bash
    cd applications/api
    uvicorn app.main:app --reload
    ```
5.  **Benchmark:** `python applications/api/eval/benchmark.py`.
