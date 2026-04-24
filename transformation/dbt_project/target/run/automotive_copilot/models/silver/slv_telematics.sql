
  create or replace   view AI_PROJECT_DB.DBT_MODELS.slv_telematics
  
   as (
    

-- SILVER LAYER: Data Cleansing and Standardization
-- We take the raw telemetry and filter out anomalies so the BI team gets clean data.

WITH raw_data AS (
    SELECT 
        VIN AS vin_reference,
        ENGINE_TEMP AS engine_temperature_celsius,
        ERROR_CODE AS diagnostic_error_code
    FROM AI_PROJECT_DB.STAGING.BRONZE_TELEMATICS
)

SELECT *
FROM raw_data
-- Guardrail: Ensure realistic engine temperatures and filter out null P-Codes
WHERE engine_temperature_celsius BETWEEN -50 AND 250
  AND diagnostic_error_code != 'NONE'
  );

