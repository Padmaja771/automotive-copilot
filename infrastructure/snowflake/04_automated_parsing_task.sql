-- ==========================================================
-- 04_AUTOMATED_PARSING_TASK.SQL
-- Orchestrates the AI processing when files arrive in S3
-- ==========================================================

USE ROLE CORTEX_DEV_ROLE;
USE DATABASE AI_PROJECT_DB;
USE SCHEMA STAGING;

-- 1. Create a stored procedure to process pending files
CREATE OR REPLACE PROCEDURE PROCESS_PENDING_PDFS()
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
DECLARE
    file_record RECORD;
    count_processed INTEGER DEFAULT 0;
BEGIN
    -- Loop through pending files
    FOR file_record IN (SELECT * FROM PENDING_INGESTION WHERE status = 'PENDING') LOOP
        
        -- Update status to PROCESSING
        UPDATE PENDING_INGESTION 
        SET status = 'PROCESSING' 
        WHERE ingestion_id = :file_record.ingestion_id;

        BEGIN
            -- Run Cortex PARSE_DOCUMENT and insert into results table
            -- We reference the filename stored in S3_MANUALS_STAGE
            INSERT INTO VEHICLE_MANUALS_PARSED (source_file, vin_reference, chunk_text, chunk_index)
            SELECT 
                :file_record.filename as source_file,
                :file_record.vin_reference as vin_reference,
                f.value AS chunk_text,
                f.index AS chunk_index
            FROM TABLE(
                SNOWFLAKE.CORTEX.PARSE_DOCUMENT(
                    @S3_MANUALS_STAGE,
                    :file_record.filename,
                    {'mode': 'LAYOUT'}
                )
            ),
            LATERAL FLATTEN(INPUT => content) f;

            -- Mark as COMPLETED
            UPDATE PENDING_INGESTION 
            SET status = 'COMPLETED', processed_at = CURRENT_TIMESTAMP()
            WHERE ingestion_id = :file_record.ingestion_id;
            
            count_processed := count_processed + 1;
            
        EXCEPTION
            WHEN OTHER THEN
                -- Mark as FAILED and log error
                UPDATE PENDING_INGESTION 
                SET status = 'FAILED', error_message = :SQLERRM, processed_at = CURRENT_TIMESTAMP()
                WHERE ingestion_id = :file_record.ingestion_id;
        END;
    END LOOP;

    RETURN 'Processed ' || CAST(:count_processed AS STRING) || ' files.';
END;
$$;

-- 2. Create a Snowflake Task to run the processor every 5 minutes
--    Note: This requires EXECUTE TASK privilege on the account
CREATE OR REPLACE TASK T_PROCESS_PDFS_TASK
    WAREHOUSE = AI_PROJECT_WH
    SCHEDULE = '5 MINUTE'
    WHEN SYSTEM$STREAM_HAS_DATA('PENDING_INGESTION_STREAM') -- Only run if there is new data
AS
    CALL PROCESS_PENDING_PDFS();

-- 3. Create a Stream on the pending table to trigger the task efficiently
CREATE OR REPLACE STREAM PENDING_INGESTION_STREAM ON TABLE PENDING_INGESTION;

-- 4. Enable the task (tasks are created suspended)
-- ALTER TASK T_PROCESS_PDFS_TASK RESUME;
