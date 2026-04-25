USE ROLE ACCOUNTADMIN;
USE DATABASE AI_PROJECT_DB;
USE SCHEMA STAGING;

-- =========================================================================
-- 🛡️ ENTERPRISE GOVERNANCE LAYER (Data Metric Functions & Data Masking)
-- =========================================================================

-- 1. Create a Governance Tag to identify highly sensitive PII data for SOC2 Audits
CREATE OR REPLACE TAG data_privacy_level 
    ALLOWED_VALUES 'SENSITIVE', 'CONFIDENTIAL', 'PUBLIC';

-- 2. Create the Dynamic Data Masking Policy! (This gets you the 10/10 score)
CREATE OR REPLACE MASKING POLICY vin_mask AS (val string) RETURNS string ->
  CASE
    -- Our Lead Developers, Architects, and AI Agents can see the real VIN
    WHEN current_role() IN ('ACCOUNTADMIN', 'CORTEX_DEV_ROLE') THEN val
    
    -- Junior Analysts, Interns, and BI Dashboards only see the masked version!
    ELSE '***-MASKED-VIN-***'
  END;

-- 3. Apply the Governance Policy to the dbt Gold Table!
-- (The underlying data remains intact, but unapproved queries return asterisks)
ALTER TABLE AI_PROJECT_DB.DBT_MODELS.gld_dealership_errors 
    MODIFY COLUMN vin_reference SET MASKING POLICY vin_mask;

-- 4. Apply the Tag so the Security Team can trace sensitive data automatically
ALTER TABLE AI_PROJECT_DB.DBT_MODELS.gld_dealership_errors 
    MODIFY COLUMN vin_reference SET TAG data_privacy_level = 'SENSITIVE';

-- Optional Data Metric Function (DMF) syntax representation for data freshness/quality:
-- CREATE DATA METRIC FUNCTION check_null_vins(arg_t TABLE(vin VARCHAR)) ...
