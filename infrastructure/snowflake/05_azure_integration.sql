-- ==========================================================
-- 05_AZURE_INTEGRATION.SQL
-- Sets up the multi-cloud ingestion path from Azure Blob Storage
-- ==========================================================

USE ROLE ACCOUNTADMIN;

-- 1. Create the Storage Integration connected to Azure Active Directory
-- In a real environment, you take the AZURE_CONSENT_URL output from this command
-- and have your Azure Global Admin approve it.
CREATE OR REPLACE STORAGE INTEGRATION AZURE_VEHICLE_DOCS_INT
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'AZURE'
  ENABLED = TRUE
  AZURE_TENANT_ID = '<your-azure-tenant-id>'
  STORAGE_ALLOWED_LOCATIONS = ('azure://autocopilotdocsdev.blob.core.windows.net/incoming/');

-- Grant access to our engineering role
GRANT USAGE ON INTEGRATION AZURE_VEHICLE_DOCS_INT TO ROLE CORTEX_DEV_ROLE;

-- 2. Create the External Stage mapping to the Azure Blob Container
USE ROLE CORTEX_DEV_ROLE;
USE DATABASE AI_PROJECT_DB;
USE SCHEMA STAGING;

CREATE OR REPLACE STAGE AZURE_MANUALS_STAGE
  URL = 'azure://autocopilotdocsdev.blob.core.windows.net/incoming/'
  STORAGE_INTEGRATION = AZURE_VEHICLE_DOCS_INT
  DIRECTORY = (ENABLE = TRUE);

-- 3. Now our existing dbt models can easily be refactored to query both 
-- @S3_MANUALS_STAGE and @AZURE_MANUALS_STAGE dynamically!
