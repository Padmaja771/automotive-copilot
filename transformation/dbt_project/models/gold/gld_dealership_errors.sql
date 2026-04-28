{{ config(materialized='table') }}

-- =========================================================================
-- GOLD LAYER: Aggregated Business-Level Facts & Vector Store
-- Standard: Pre-compute AI embeddings at the Data Warehouse layer.
-- This table is ready for the Dealership Dashboard and Cortex AI vector routing.
-- =========================================================================

WITH silver_telematics AS (
    SELECT * FROM {{ ref('slv_telematics') }}
)

SELECT 
    vin_reference,
    COUNT(diagnostic_error_code) AS total_critical_errors,
    MAX(engine_temperature_celsius) AS max_engine_temp_recorded,
    
    -- Combine structured data and AI summaries into a rich context string
    ARRAY_AGG(log_summary) AS full_vehicle_history_summaries,
    ARRAY_AGG(fault_category) AS distinct_fault_categories,

    -- 🤖 CORTEX NATIVE: Pre-compute Vector Embeddings for the entire vehicle history
    -- Instead of the Python API doing this on-the-fly, it's instant in SQL.
    SNOWFLAKE.CORTEX.EMBED_TEXT_768(
        'snowflake-arctic-embed-m-v1.5',
        CONCAT('Vehicle ', vin_reference, ' history: ', ARRAY_TO_STRING(ARRAY_AGG(log_summary), ' | '))
    ) AS vehicle_history_embedding,

    CURRENT_TIMESTAMP() AS last_aggregated_at
FROM silver_telematics
GROUP BY vin_reference
