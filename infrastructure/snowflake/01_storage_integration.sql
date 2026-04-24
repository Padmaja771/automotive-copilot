-- ==========================================================
-- 01_STORAGE_INTEGRATION.SQL
-- Creates the trust bridge between Snowflake and AWS S3
-- ==========================================================
-- Run as ACCOUNTADMIN (one-time setup)
-- ==========================================================

USE ROLE ACCOUNTADMIN;

-- 1. Create the Storage Integration
--    Replace <your-bucket> and <your-role-arn> with Terraform outputs
CREATE OR REPLACE STORAGE INTEGRATION S3_VEHICLE_DOCS_INT
    TYPE = EXTERNAL_STAGE
    STORAGE_PROVIDER = 'S3'
    ENABLED = TRUE
    STORAGE_AWS_ROLE_ARN = '<snowflake_s3_role_arn from terraform output>'
    STORAGE_ALLOWED_LOCATIONS = ('s3://<s3_bucket_name from terraform output>/incoming/');

-- 2. Describe the integration to get the values needed for Terraform
--    Copy STORAGE_AWS_IAM_USER_ARN and STORAGE_AWS_EXTERNAL_ID
--    back into your terraform.tfvars file
DESC INTEGRATION S3_VEHICLE_DOCS_INT;

-- 3. Grant usage to the developer role
GRANT USAGE ON INTEGRATION S3_VEHICLE_DOCS_INT TO ROLE CORTEX_DEV_ROLE;
