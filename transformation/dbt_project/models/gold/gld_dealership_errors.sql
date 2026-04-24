{{ config(materialized='table') }}

-- GOLD LAYER: Aggregated Business-Level Facts
-- This table is ready for the Dealership Dashboard and Cortex AI routing.

WITH silver_telematics AS (
    SELECT * FROM {{ ref('slv_telematics') }}
)

SELECT 
    vin_reference,
    COUNT(diagnostic_error_code) AS total_critical_errors,
    MAX(engine_temperature_celsius) AS max_engine_temp_recorded,
    CURRENT_TIMESTAMP() AS last_aggregated_at
FROM silver_telematics
GROUP BY vin_reference
