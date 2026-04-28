{{ config(materialized='table') }}

-- =========================================================================
-- SILVER LAYER: Cortex AI Fault Analysis
-- Standard: The "Masterpiece" model demonstrating 3 native Cortex functions.
-- Extracts sentiment, summaries, and structured answers directly in SQL.
-- =========================================================================

WITH raw_telemetry AS (
    SELECT 
        -- Creating a deterministic fault ID for the table
        MD5(CONCAT(VIN, RECORDED_AT, ERROR_CODE)) AS fault_id,
        
        -- Governance: Masking the VIN for analysts who query this table
        -- (Assuming a Dynamic Data Masking policy applies to the raw table,
        -- but we enforce structural masking here for demonstration)
        CONCAT('***-***-', RIGHT(VIN, 4)) AS vin_masked,
        
        LOG_TEXT AS raw_log,
        RECORDED_AT AS recorded_at
    FROM AI_PROJECT_DB.STAGING.BRONZE_TELEMATICS
    WHERE LOG_TEXT IS NOT NULL
      AND LOG_TEXT != ''
)

SELECT 
    fault_id,
    vin_masked,
    recorded_at,
    raw_log,
    
    -- 🤖 CORTEX SKILL 1: The "Heavy Lifting" Sentiment Analysis
    -- Detects driver frustration to prioritize urgent complaints
    SNOWFLAKE.CORTEX.SENTIMENT(raw_log) AS driver_frustration_score,
    
    -- 🤖 CORTEX SKILL 2: Auto-Summarization
    -- Reduces paragraph-long mechanics notes into a single concise sentence
    SNOWFLAKE.CORTEX.SUMMARIZE(raw_log) AS concise_fault_summary,
    
    -- 🤖 CORTEX SKILL 3: RAG Extraction from Unstructured Data
    -- Pulls out the specific structured data point from messy text
    SNOWFLAKE.CORTEX.EXTRACT_ANSWER(
        raw_log, 
        'What was the specific vehicle component mentioned?'
    )::VARIANT AS target_component_extracted

FROM raw_telemetry
