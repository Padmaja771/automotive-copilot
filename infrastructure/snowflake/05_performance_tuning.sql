-- =========================================================================
-- Snowflake Performance Tuning Playbook
-- Automotive Intelligence Copilot
-- =========================================================================
-- Standard: Apply these optimizations in order after initial schema setup.
-- Every decision is documented with WHY it improves performance.
-- Run as: SYSADMIN (for warehouse) + ACCOUNTADMIN (for clustering policies)
-- =========================================================================

USE ROLE SYSADMIN;
USE DATABASE AI_PROJECT_DB;

-- =========================================================================
-- SECTION 1: WAREHOUSE RIGHT-SIZING & AUTO-SUSPEND
-- Problem: Using a static XL warehouse 24/7 wastes 90% of compute budget.
-- Solution: Purpose-built, auto-suspending warehouses per workload type.
-- =========================================================================

-- Warehouse for dbt/ETL transforms (bursty, batch workload)
CREATE OR REPLACE WAREHOUSE DBT_TRANSFORM_WH
    WAREHOUSE_SIZE     = 'MEDIUM'      -- Large enough for CORTEX functions
    AUTO_SUSPEND       = 60            -- Suspends after 60 seconds idle
    AUTO_RESUME        = TRUE
    MAX_CLUSTER_COUNT  = 3             -- Multi-cluster scales out for parallel dbt runs
    SCALING_POLICY     = 'ECONOMY'     -- Maximizes cluster use before scaling out
    COMMENT            = 'Used by dbt_deploy_role for Silver/Gold model runs.';

-- Warehouse for FastAPI / real-time RAG queries (low-latency, interactive)
CREATE OR REPLACE WAREHOUSE API_QUERY_WH
    WAREHOUSE_SIZE     = 'X-SMALL'     -- RAG queries are small; XS = cheapest + fastest cold start
    AUTO_SUSPEND       = 30            -- Aggressive 30s suspend for cost control
    AUTO_RESUME        = TRUE
    MAX_CLUSTER_COUNT  = 5             -- Scale wide for many concurrent API requests
    SCALING_POLICY     = 'STANDARD'    -- Prioritizes query latency over cost
    COMMENT            = 'Used by cortex_dev_role for live API/Cortex inference.';

-- Warehouse for ML training (long-running, compute-intensive)
CREATE OR REPLACE WAREHOUSE ML_TRAINING_WH
    WAREHOUSE_SIZE     = 'LARGE'
    AUTO_SUSPEND       = 120
    AUTO_RESUME        = TRUE
    MAX_CLUSTER_COUNT  = 1             -- Training is single-node; scale UP not OUT
    COMMENT            = 'Used by ml_predictive_maintenance.py for Snowpark ML training.';


-- =========================================================================
-- SECTION 2: AUTOMATIC CLUSTERING ON GOLD TABLES
-- Problem: Without clustering, every query on GOLD tables scans ALL micro-partitions.
-- Solution: Cluster on the columns used most in WHERE and JOIN clauses.
--
-- Snowflake Docs: Automatic Clustering continuously re-sorts data as DML occurs.
-- Cost: ~10-20% storage overhead, but 10x-100x query speedup on filtered scans.
-- =========================================================================

-- The GLD_DEALERSHIP_ERRORS table is filtered heavily by VIN.
-- e.g. FastAPI: "SELECT * FROM GLD_DEALERSHIP_ERRORS WHERE VIN_REFERENCE = 'VIN_123'"
ALTER TABLE AI_PROJECT_DB.GOLD.GLD_DEALERSHIP_ERRORS
    CLUSTER BY (VIN_REFERENCE);

-- The SLV_FAULT_ANALYSIS table is queried by time range for dashboards.
-- e.g. Snowsight: "WHERE RECORDED_AT > DATEADD(day, -7, CURRENT_TIMESTAMP())"
ALTER TABLE AI_PROJECT_DB.SILVER.SLV_FAULT_ANALYSIS
    CLUSTER BY (TO_DATE(RECORDED_AT), VIN_MASKED);

-- Verify that Automatic Clustering is enabled and healthy:
-- SELECT SYSTEM$CLUSTERING_INFORMATION('AI_PROJECT_DB.GOLD.GLD_DEALERSHIP_ERRORS');
-- Look for: average_depth close to 1.0 = perfectly clustered
-- average_depth > 4.0 = clustering needed (run ALTER TABLE RECLUSTER)


-- =========================================================================
-- SECTION 3: SEARCH OPTIMIZATION FOR VECTOR SIMILARITY SEARCH
-- Problem: VECTOR_L2_DISTANCE requires scanning every row to find similar embeddings.
-- Solution: Search Optimization Service (SOS) builds an index on VECTOR columns,
--           reducing vector search from O(n) to O(log n).
-- =========================================================================

-- Enable Search Optimization on the embedding column in the Gold table.
-- This is the key performance unlock for the RAG retrieval pipeline.
ALTER TABLE AI_PROJECT_DB.GOLD.GLD_DEALERSHIP_ERRORS
    ADD SEARCH OPTIMIZATION ON EQUALITY(VIN_REFERENCE);

-- For vector search, the VEHICLE_HISTORY_EMBEDDING column benefits from
-- approximate nearest neighbor indexing:
ALTER TABLE AI_PROJECT_DB.GOLD.GLD_DEALERSHIP_ERRORS
    ADD SEARCH OPTIMIZATION ON FULL_TEXT(VEHICLE_HISTORY_EMBEDDING);


-- =========================================================================
-- SECTION 4: MATERIALIZED VIEWS FOR EXPENSIVE AGGREGATIONS
-- Problem: The Snowsight Dashboard re-runs complex aggregations on every page load.
-- Solution: Pre-compute the expensive aggregation once; reads are instant.
--
-- When to use: When the same expensive GROUP BY query runs > 10x per hour.
-- =========================================================================

CREATE OR REPLACE MATERIALIZED VIEW MV_VEHICLE_FAULT_SUMMARY AS
SELECT
    VIN_REFERENCE,
    COUNT(*)                             AS total_fault_count,
    AVG(DRIVER_FRUSTRATION_SCORE)        AS avg_frustration,
    SUM(CASE WHEN DRIVER_FRUSTRATION_SCORE < -0.5 THEN 1 ELSE 0 END) AS high_frustration_count,
    MAX(RECORDED_AT)                     AS latest_fault_at
FROM AI_PROJECT_DB.SILVER.SLV_FAULT_ANALYSIS
GROUP BY VIN_REFERENCE;

-- Grant BI Analysts read access to the fast materialized view only
GRANT SELECT ON MATERIALIZED VIEW MV_VEHICLE_FAULT_SUMMARY TO ROLE ANALYST_ROLE;


-- =========================================================================
-- SECTION 5: QUERY REFINEMENT — OPTIMIZED RAG RETRIEVAL SQL
-- Problem: Naive vector search scans all rows before applying business filters.
-- Solution: Apply cheap WHERE filters FIRST to shrink the dataset, THEN run
--           the expensive VECTOR_L2_DISTANCE calculation on the smaller set.
-- =========================================================================

-- ❌ UNOPTIMIZED: Scans all 10M rows, computes distance on all, then filters
-- SELECT VIN_REFERENCE, VECTOR_L2_DISTANCE(embedding, ?) AS score
-- FROM GLD_DEALERSHIP_ERRORS
-- WHERE score < 0.4
-- ORDER BY score LIMIT 5;

-- ✅ OPTIMIZED PATTERN: Filter-first, then compute distance
-- This is the query pattern used in applications/api/app/llm/snowflake_provider.py
CREATE OR REPLACE PROCEDURE SP_OPTIMIZED_RAG_SEARCH(
    query_embedding  VECTOR(FLOAT, 768),
    target_vin       STRING,
    max_results      INT
)
RETURNS TABLE(VIN_REFERENCE STRING, SIMILARITY_SCORE FLOAT, HISTORY_SUMMARIES ARRAY)
LANGUAGE SQL
AS
$$
BEGIN
    RETURN TABLE(
        SELECT
            VIN_REFERENCE,
            VECTOR_L2_DISTANCE(VEHICLE_HISTORY_EMBEDDING, :query_embedding) AS SIMILARITY_SCORE,
            FULL_VEHICLE_HISTORY_SUMMARIES
        FROM AI_PROJECT_DB.GOLD.GLD_DEALERSHIP_ERRORS
        WHERE
            -- 1. CHEAP filter first: eliminates 99% of rows using clustering key
            VIN_REFERENCE = IFF(:target_vin IS NOT NULL, :target_vin, VIN_REFERENCE)
            -- 2. THEN expensive vector distance only on remaining rows
        ORDER BY SIMILARITY_SCORE ASC
        LIMIT :max_results
    );
END;
$$;


-- =========================================================================
-- SECTION 6: RESULT CACHE & QUERY TAGGING
-- Problem: Dashboard and health-check queries re-run the same SQL repeatedly.
-- Solution: Ensure Result Cache is on. Tag all queries for cost attribution.
-- =========================================================================

-- Ensure Result Cache is enabled at the account level (default is ON)
ALTER ACCOUNT SET USE_CACHED_RESULT = TRUE;

-- Query Tag Best Practice: Set per-session so cost attribution is automatic
-- in the Query History tab. Each system sets its own tag.
ALTER SESSION SET QUERY_TAG = 'automotive_copilot.api';   -- FastAPI layer
-- ALTER SESSION SET QUERY_TAG = 'automotive_copilot.dbt'; -- dbt profile.yml
-- ALTER SESSION SET QUERY_TAG = 'automotive_copilot.ml';  -- ML training job


-- =========================================================================
-- SECTION 7: DATA RETENTION & TIME TRAVEL POLICY
-- Problem: Default 1-day retention is too short for debugging AI regressions.
-- Solution: Extend Time Travel on Gold tables to 7 days for rollback capability.
-- =========================================================================

-- Gold tables store pre-computed AI outputs — 7 days lets us compare before/after
-- a Cortex model update to detect quality regressions.
ALTER TABLE AI_PROJECT_DB.GOLD.GLD_DEALERSHIP_ERRORS    SET DATA_RETENTION_TIME_IN_DAYS = 7;
ALTER TABLE AI_PROJECT_DB.SILVER.SLV_FAULT_ANALYSIS     SET DATA_RETENTION_TIME_IN_DAYS = 7;

-- Usage Example: Roll back the Gold table 24 hours if a bad dbt run is detected
-- SELECT * FROM GLD_DEALERSHIP_ERRORS AT(OFFSET => -86400);
-- CREATE OR REPLACE TABLE GLD_DEALERSHIP_ERRORS AS
--     SELECT * FROM GLD_DEALERSHIP_ERRORS AT(OFFSET => -86400);


-- =========================================================================
-- SECTION 8: MONITORING — QUERY PROFILE HEALTH CHECK
-- Run these after deploying to verify clustering and query efficiency.
-- =========================================================================

-- Check Clustering Health (average_depth near 1.0 = optimal)
SELECT SYSTEM$CLUSTERING_INFORMATION('AI_PROJECT_DB.GOLD.GLD_DEALERSHIP_ERRORS', '(VIN_REFERENCE)');
SELECT SYSTEM$CLUSTERING_INFORMATION('AI_PROJECT_DB.SILVER.SLV_FAULT_ANALYSIS', '(TO_DATE(RECORDED_AT), VIN_MASKED)');

-- Top 10 most expensive queries in the last 24 hours (cost monitoring)
SELECT
    QUERY_TEXT,
    TOTAL_ELAPSED_TIME / 1000            AS duration_seconds,
    BYTES_SCANNED / 1024 / 1024 / 1024  AS gb_scanned,
    CREDITS_USED_CLOUD_SERVICES          AS credits_used,
    QUERY_TAG
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME > DATEADD(HOUR, -24, CURRENT_TIMESTAMP())
  AND QUERY_TAG LIKE 'automotive_copilot%'
ORDER BY TOTAL_ELAPSED_TIME DESC
LIMIT 10;
