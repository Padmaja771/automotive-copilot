{{ config(materialized='view') }}

-- =========================================================================
-- SILVER LAYER: Telematics & AI Enrichment
-- Standard: Shift AI logic left into the database using Snowflake Cortex.
-- We take raw mechanic logs, clean them, summarize them, and categorize them.
-- =========================================================================

WITH raw_data AS (
    SELECT 
        VIN AS vin_reference,
        ENGINE_TEMP AS engine_temperature_celsius,
        ERROR_CODE AS diagnostic_error_code,
        LOG_TEXT AS mechanic_notes
    FROM AI_PROJECT_DB.STAGING.BRONZE_TELEMATICS
    WHERE ERROR_CODE != 'NONE' 
      AND ENGINE_TEMP BETWEEN -50 AND 250
)

SELECT 
    vin_reference,
    diagnostic_error_code,
    engine_temperature_celsius,
    mechanic_notes,
    
    -- 🤖 CORTEX NATIVE: Auto-summarize lengthy mechanic notes
    SNOWFLAKE.CORTEX.SUMMARIZE(mechanic_notes) AS log_summary,
    
    -- 🤖 CORTEX NATIVE: Classify the issue using a fast LLM
    SNOWFLAKE.CORTEX.COMPLETE(
        'mistral-large2',
        CONCAT(
            'Classify the following vehicle log into exactly one category: [ENGINE, ELECTRICAL, BRAKES, TRANSMISSION, OTHER]. ',
            'Log: ', mechanic_notes,
            ' Return ONLY the category name.'
        )
    ) AS fault_category

FROM raw_data
