{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('staging', 'PENDING_INGESTION') }}
)

SELECT
    ingestion_id,
    filename AS source_file,
    vin_reference,
    s3_key,
    file_size_mb,
    status,
    received_at
FROM source
WHERE status = 'PENDING'
