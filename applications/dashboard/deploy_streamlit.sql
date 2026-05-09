-- =========================================================================
-- Deploy Streamlit-in-Snowflake Dashboard
-- Run as SYSADMIN after uploading streamlit_app.py to a Snowflake stage.
-- =========================================================================

USE ROLE SYSADMIN;
USE DATABASE AI_PROJECT_DB;
USE SCHEMA STAGING;
USE WAREHOUSE API_QUERY_WH;

-- 1. Upload the app file to a named stage (run via SnowSQL CLI):
-- PUT file://applications/dashboard/streamlit_app.py @AI_PROJECT_DB.STAGING.APP_STAGE
--     AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

-- 2. Create the Streamlit App inside Snowflake
CREATE OR REPLACE STREAMLIT AUTOMOTIVE_COPILOT_DASHBOARD
    ROOT_LOCATION    = '@AI_PROJECT_DB.STAGING.APP_STAGE'
    MAIN_FILE        = 'streamlit_app.py'
    QUERY_WAREHOUSE  = 'API_QUERY_WH'
    COMMENT          = 'Automotive Intelligence Copilot — Fleet Health + Live AI Diagnostics';

-- 3. Grant ANALYST_ROLE access to view the dashboard in Snowsight
GRANT USAGE ON STREAMLIT AUTOMOTIVE_COPILOT_DASHBOARD TO ROLE ANALYST_ROLE;
GRANT USAGE ON STREAMLIT AUTOMOTIVE_COPILOT_DASHBOARD TO ROLE CORTEX_DEV_ROLE;

-- 4. View the app URL
SHOW STREAMLITS LIKE 'AUTOMOTIVE_COPILOT_DASHBOARD';
