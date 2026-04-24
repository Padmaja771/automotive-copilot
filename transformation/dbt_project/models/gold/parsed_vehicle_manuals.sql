{{ config(materialized='table') }}

WITH pending_files AS (
    SELECT * FROM {{ ref('stg_pending_files') }}
)

SELECT 
    pf.source_file,
    pf.vin_reference,
    f.value::string AS chunk_text,
    f.index AS chunk_index,
    CURRENT_TIMESTAMP() AS extracted_at
FROM pending_files pf,
     TABLE(SNOWFLAKE.CORTEX.PARSE_DOCUMENT(
         '@AI_PROJECT_DB.STAGING.S3_MANUALS_STAGE',
         pf.source_file,
         {'mode': 'LAYOUT'}
     )) doc,
     LATERAL FLATTEN(INPUT => doc.content) f
