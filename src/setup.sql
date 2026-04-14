-- ==========================================================
-- 01_ENVIRONMENT_SETUP.SQL
-- Automotive Intelligence Copilot Setup
-- ==========================================================

USE ROLE ACCOUNTADMIN;
CREATE ROLE IF NOT EXISTS CORTEX_DEV_ROLE;
GRANT ROLE CORTEX_DEV_ROLE TO USER CURRENT_USER();

CREATE DATABASE IF NOT EXISTS AI_PROJECT_DB;
CREATE SCHEMA IF NOT EXISTS AI_PROJECT_DB.STAGING;
CREATE WAREHOUSE IF NOT EXISTS AI_PROJECT_WH WAREHOUSE_SIZE = 'XSMALL' AUTO_SUSPEND = 60;

GRANT USAGE ON WAREHOUSE AI_PROJECT_WH TO ROLE CORTEX_DEV_ROLE;
GRANT ALL PRIVILEGES ON DATABASE AI_PROJECT_DB TO ROLE CORTEX_DEV_ROLE;
GRANT ALL PRIVILEGES ON SCHEMA AI_PROJECT_DB.STAGING TO ROLE CORTEX_DEV_ROLE;

GRANT USE AI FUNCTIONS ON ACCOUNT TO ROLE CORTEX_DEV_ROLE;
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE CORTEX_DEV_ROLE;

-- ==========================================================
-- 02_DATA_MODEL.SQL
-- Automotive Data Schemas
-- ==========================================================

USE ROLE CORTEX_DEV_ROLE;
USE DATABASE AI_PROJECT_DB;
USE SCHEMA STAGING;

-- Table for Vehicle Manuals & Diagnostic Records
CREATE OR REPLACE TABLE VEHICLE_INTELLIGENCE_DATA (
    record_id NUMBER AUTOINCREMENT,
    vin STRING,
    data_type STRING, -- 'MANUAL', 'SERVICE_LOG', 'DIAGNOSTIC'
    content_text STRING,
    ingested_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Insert Synthetic Automotive Data
INSERT INTO VEHICLE_INTELLIGENCE_DATA (vin, data_type, content_text) VALUES 
('VIN123', 'DIAGNOSTIC', 'Error Code P0300 detected. Multiple cylinder misfire. Engine vibrating at high speeds. Fuel pressure normal.'),
('VIN123', 'MANUAL', 'For misfire issues (P0300), inspect spark plugs and ignition coils. Torque specification: 15-20 lb-ft.'),
('VIN456', 'SERVICE_LOG', 'Customer complains of "squealing" noise during braking. Inspected pads; found 20% life remaining. Recommended replacement.'),
('VIN456', 'MANUAL', 'Brake pad minimum thickness: 2mm. Squealing may indicate acoustic wear indicator is engaged.');

-- Intelligence Query Test
SELECT 
    vin,
    SNOWFLAKE.CORTEX.SUMMARIZE(content_text) as ai_summary,
    SNOWFLAKE.CORTEX.EXTRACT_ANSWER(content_text, 'What is the specific fix or technical spec mentioned?') as technical_fix
FROM VEHICLE_INTELLIGENCE_DATA;
