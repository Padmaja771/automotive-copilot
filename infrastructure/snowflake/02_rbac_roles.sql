-- ============================================================
-- Snowflake RBAC Governance Setup
-- Standard: Principle of Least Privilege
-- ACCOUNTADMIN is ONLY used here (infra setup), never in app code.
-- ============================================================

USE ROLE ACCOUNTADMIN;

-- ─────────────────────────────────────────────
-- 1. Create Least-Privilege Application Roles
-- ─────────────────────────────────────────────
CREATE ROLE IF NOT EXISTS CORTEX_DEV_ROLE
    COMMENT = 'Application role for Cortex LLM inference and vector search. Cannot modify schema.';

CREATE ROLE IF NOT EXISTS ANALYST_ROLE
    COMMENT = 'Read-only role for dbt analysts and Snowsight dashboard users. PII is masked.';

CREATE ROLE IF NOT EXISTS DBT_DEPLOY_ROLE
    COMMENT = 'CI/CD role for dbt model deployment. Can CREATE/REPLACE views and tables.';

-- ─────────────────────────────────────────────
-- 2. Grant Warehouse Access (Compute)
-- ─────────────────────────────────────────────
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE CORTEX_DEV_ROLE;
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE ANALYST_ROLE;
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE DBT_DEPLOY_ROLE;

-- ─────────────────────────────────────────────
-- 3. Grant Database Permissions
-- ─────────────────────────────────────────────
GRANT USAGE ON DATABASE AI_PROJECT_DB TO ROLE CORTEX_DEV_ROLE;
GRANT USAGE ON DATABASE AI_PROJECT_DB TO ROLE ANALYST_ROLE;
GRANT USAGE ON DATABASE AI_PROJECT_DB TO ROLE DBT_DEPLOY_ROLE;

-- ─────────────────────────────────────────────
-- 4. Schema-Level Grants
-- ─────────────────────────────────────────────
-- CORTEX_DEV_ROLE: Can read all Snowflake objects and call Cortex functions
GRANT USAGE ON ALL SCHEMAS IN DATABASE AI_PROJECT_DB TO ROLE CORTEX_DEV_ROLE;
GRANT SELECT ON ALL TABLES IN DATABASE AI_PROJECT_DB TO ROLE CORTEX_DEV_ROLE;

-- ANALYST_ROLE: Read-only (PII masked via Dynamic Data Masking)
GRANT USAGE ON ALL SCHEMAS IN DATABASE AI_PROJECT_DB TO ROLE ANALYST_ROLE;
GRANT SELECT ON ALL TABLES IN DATABASE AI_PROJECT_DB TO ROLE ANALYST_ROLE;

-- DBT_DEPLOY_ROLE: Can create/replace models in Bronze, Silver, Gold schemas
GRANT ALL PRIVILEGES ON SCHEMA AI_PROJECT_DB.BRONZE TO ROLE DBT_DEPLOY_ROLE;
GRANT ALL PRIVILEGES ON SCHEMA AI_PROJECT_DB.SILVER TO ROLE DBT_DEPLOY_ROLE;
GRANT ALL PRIVILEGES ON SCHEMA AI_PROJECT_DB.GOLD TO ROLE DBT_DEPLOY_ROLE;

-- ─────────────────────────────────────────────
-- 5. Assign Roles to Service Users
-- ─────────────────────────────────────────────
GRANT ROLE CORTEX_DEV_ROLE TO USER FASTAPI_SERVICE_USER;
GRANT ROLE ANALYST_ROLE    TO USER ANALYST_USER;
GRANT ROLE DBT_DEPLOY_ROLE TO USER DBT_CI_USER;

-- ─────────────────────────────────────────────
-- 6. Cortex AI Usage Permissions
-- ─────────────────────────────────────────────
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE CORTEX_DEV_ROLE;
