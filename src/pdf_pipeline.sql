-- ==========================================================
-- 04_PDF_PIPELINE.SQL  
-- Snowflake Stage + Document Intelligence Pipeline
-- ==========================================================

USE ROLE CORTEX_DEV_ROLE;
USE DATABASE AI_PROJECT_DB;
USE SCHEMA STAGING;

-- 1. Create an internal Snowflake Stage to hold uploaded PDF files
CREATE OR REPLACE STAGE MANUALS_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'Internal stage for raw Vehicle Manual PDFs';

-- 2. Create a table to store extracted text chunks from PDFs
CREATE OR REPLACE TABLE VEHICLE_MANUALS_PARSED (
    manual_id NUMBER AUTOINCREMENT,
    source_file STRING,
    vin_reference STRING,
    chunk_text STRING,
    chunk_index NUMBER,
    extracted_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 3. After running the Python uploader (ingest_pdfs.py), 
--    run THIS query to parse all uploaded PDFs using Cortex Doc AI:
INSERT INTO VEHICLE_MANUALS_PARSED (source_file, vin_reference, chunk_text, chunk_index)
SELECT 
    METADATA$FILENAME as source_file,
    SPLIT_PART(METADATA$FILENAME, '_', 1) as vin_reference,
    f.value AS chunk_text,
    f.index AS chunk_index
FROM @MANUALS_STAGE,
LATERAL FLATTEN(
    INPUT => SNOWFLAKE.CORTEX.PARSE_DOCUMENT(
        @MANUALS_STAGE,
        METADATA$FILENAME,
        {'mode': 'LAYOUT'}
    ):content
) f
WHERE METADATA$FILENAME LIKE '%.pdf';

-- 4. Verify parsed content
SELECT source_file, vin_reference, chunk_index, LEFT(chunk_text, 200) as preview
FROM VEHICLE_MANUALS_PARSED 
ORDER BY manual_id;
