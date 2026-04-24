-- ==========================================================
-- 03_EXTERNAL_STAGE.SQL
-- Creates the link to the S3 bucket using the Integration
-- ==========================================================

USE ROLE CORTEX_DEV_ROLE;
USE DATABASE AI_PROJECT_DB;
USE SCHEMA STAGING;

-- Create the external stage
-- Replace <s3_bucket_name> with the bucket name from Terraform output
CREATE OR REPLACE STAGE S3_MANUALS_STAGE
    URL = 's3://<s3_bucket_name>/incoming/'
    STORAGE_INTEGRATION = S3_VEHICLE_DOCS_INT
    DIRECTORY = (ENABLE = TRUE);

-- Refresh the directory to see files
ALTER STAGE S3_MANUALS_STAGE REFRESH;
