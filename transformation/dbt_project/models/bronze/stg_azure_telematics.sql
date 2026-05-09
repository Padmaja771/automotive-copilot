{{ config(materialized='view') }}

-- =========================================================================
-- BRONZE LAYER: Staging Azure Extended Telematics
-- Standard: Raw ingestion from Azure Event Hub / Blob Storage via Snowflake Stage
-- =========================================================================

WITH raw_azure_data AS (
    -- In a real scenario, this would select from an external stage or a landing table
    -- For this demo, we simulate the structure of the JSON data
    SELECT 
        $1:vin::STRING                 AS vin_reference,
        $1:engine_temp_c::FLOAT        AS engine_temp,
        $1:error_code::STRING          AS error_code,
        $1:cloud_source::STRING        AS source_system,
        $1:service_center_id::STRING   AS service_center,
        $1:mechanic_notes::STRING      AS raw_notes,
        $1:parts_on_order::VARIANT     AS pending_parts,
        $1:customer_sentiment_raw::STRING AS raw_sentiment,
        CURRENT_TIMESTAMP()            AS ingested_at
    FROM @AI_PROJECT_DB.STAGING.AZURE_EXT_STAGE (FILE_FORMAT => 'JSON_FORMAT')
)

SELECT * FROM raw_azure_data
