-- ==========================================================
-- 02_INGESTION_TABLES.SQL
-- Tables for tracking and storing PDF extractions
-- ==========================================================

USE ROLE CORTEX_DEV_ROLE;
USE DATABASE AI_PROJECT_DB;
USE SCHEMA STAGING;

-- 1. Table for tracking files arriving from AWS S3
--    This is where the Lambda inserts metadata
CREATE OR REPLACE TABLE PENDING_INGESTION (
    ingestion_id NUMBER AUTOINCREMENT,
    s3_bucket STRING,
    s3_key STRING,
    filename STRING,
    vin_reference STRING,
    status STRING DEFAULT 'PENDING', -- PENDING, PROCESSING, COMPLETED, FAILED
    error_message STRING,
    file_size_mb FLOAT,
    received_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    processed_at TIMESTAMP_NTZ
);

-- 2. Final table for AI-extracted content chunks
--    We use this for our RAG Copilot
CREATE OR REPLACE TABLE VEHICLE_MANUALS_PARSED (
    manual_id NUMBER AUTOINCREMENT,
    source_file STRING,
    vin_reference STRING,
    chunk_text STRING,
    chunk_index NUMBER,
    extracted_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
