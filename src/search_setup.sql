-- ==========================================================
-- 03_SEARCH_INDEX.SQL
-- Creating the Cortex Semantic Search Service for RAG
-- ==========================================================

USE ROLE CORTEX_DEV_ROLE;
USE DATABASE AI_PROJECT_DB;
USE SCHEMA STAGING;

-- Create the Cortex Vector Search Index over our unstructured text
CREATE OR REPLACE CORTEX SEARCH SERVICE VEHICLE_DOCS_SEARCH
    ON content_text
    ATTRIBUTES vin, data_type
    WAREHOUSE = AI_PROJECT_WH
    TARGET_LAG = '1 minute'
    AS (
        SELECT 
            vin,
            data_type,
            content_text 
        FROM AI_PROJECT_DB.STAGING.VEHICLE_INTELLIGENCE_DATA
    );

-- Give the index 10 seconds to build, then test it out:
-- Example test: Querying the service directly (if supported in your driver version):
-- SELECT PARSE_JSON(
--   SYSTEM$CORTEX_SEARCH(
--     'VEHICLE_DOCS_SEARCH',
--     '{"query": "misfire issues and torque specifications", "columns": ["vin", "content_text"], "limit": 2}'
--   )
-- );
