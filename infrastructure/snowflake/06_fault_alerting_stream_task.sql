-- =========================================================================
-- Story 1: Automated Fault Alerting — Snowflake Streams + Tasks
-- =========================================================================
-- Pattern: Change Data Capture (CDC) using a STREAM on the Gold table.
--          A TASK fires every 15 minutes, evaluates the stream, and writes
--          alert records to ALERTS.FAULT_NOTIFICATIONS for any VIN that
--          crosses the critical fault threshold.
--
-- Run as SYSADMIN (Task scheduling) + CORTEX_DEV_ROLE (data access)
-- =========================================================================

USE ROLE SYSADMIN;
USE DATABASE AI_PROJECT_DB;
USE WAREHOUSE DBT_TRANSFORM_WH;

-- ── Step 1: Create Alerts Schema & Table ──────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS AI_PROJECT_DB.ALERTS;

CREATE TABLE IF NOT EXISTS AI_PROJECT_DB.ALERTS.FAULT_NOTIFICATIONS (
    alert_id            STRING    DEFAULT UUID_STRING() PRIMARY KEY,
    vin_reference       STRING    NOT NULL,
    fault_count         INT       NOT NULL,
    max_engine_temp     FLOAT,
    battery_voltage_v   FLOAT,
    severity_label      STRING    NOT NULL,   -- LOW | HIGH | CRITICAL
    triggered_at        TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    alert_source        STRING    DEFAULT 'SNOWFLAKE_TASK',
    acknowledged        BOOLEAN   DEFAULT FALSE,
    CONSTRAINT chk_severity CHECK (severity_label IN ('LOW', 'HIGH', 'CRITICAL'))
)
DATA_RETENTION_TIME_IN_DAYS = 30
COMMENT = 'Alert log written by Task every 15 minutes from GLD_DEALERSHIP_ERRORS stream.';

-- ── Step 2: Create Stream on Gold Table (CDC) ─────────────────────────────────
-- The STREAM tracks every INSERT, UPDATE, and DELETE on GLD_DEALERSHIP_ERRORS.
-- After the Task consumes it, the stream resets to empty until the next change.
CREATE OR REPLACE STREAM AI_PROJECT_DB.ALERTS.STR_GOLD_DEALERSHIP_CHANGES
    ON TABLE AI_PROJECT_DB.GOLD.GLD_DEALERSHIP_ERRORS
    APPEND_ONLY = FALSE   -- Capture all DML: inserts + updates
    COMMENT = 'CDC stream on GLD_DEALERSHIP_ERRORS — consumed by TASK_FAULT_ALERT every 15 min';

-- ── Step 3: Stored Procedure — Alert Evaluation Logic ─────────────────────────
CREATE OR REPLACE PROCEDURE AI_PROJECT_DB.ALERTS.SP_EVALUATE_FAULT_ALERTS()
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
DECLARE
    rows_processed INT DEFAULT 0;
BEGIN
    -- Only run if the stream has new data (prevents empty runs wasting credits)
    IF (SYSTEM$STREAM_HAS_DATA('AI_PROJECT_DB.ALERTS.STR_GOLD_DEALERSHIP_CHANGES')) THEN

        MERGE INTO AI_PROJECT_DB.ALERTS.FAULT_NOTIFICATIONS tgt
        USING (
            -- Read from the stream and classify severity in one pass
            SELECT
                s.VIN_REFERENCE,
                s.TOTAL_CRITICAL_ERRORS                          AS fault_count,
                s.MAX_ENGINE_TEMP_RECORDED                       AS max_engine_temp,
                s.LAST_AGGREGATED_AT,

                -- Severity classification logic
                CASE
                    WHEN s.TOTAL_CRITICAL_ERRORS > 20
                      OR s.MAX_ENGINE_TEMP_RECORDED > 130  THEN 'CRITICAL'
                    WHEN s.TOTAL_CRITICAL_ERRORS > 10
                      OR s.MAX_ENGINE_TEMP_RECORDED > 115  THEN 'HIGH'
                    ELSE NULL   -- Below threshold: do not alert
                END AS severity_label

            FROM AI_PROJECT_DB.ALERTS.STR_GOLD_DEALERSHIP_CHANGES s
            WHERE s.METADATA$ACTION = 'INSERT'
               OR s.METADATA$ACTION = 'UPDATE'

        ) src
        ON (src.severity_label IS NOT NULL)   -- Only merge rows that breach a threshold

        -- Avoid duplicate alerts for the same VIN on the same run
        WHEN NOT MATCHED AND src.severity_label IS NOT NULL THEN
            INSERT (vin_reference, fault_count, max_engine_temp, severity_label)
            VALUES (src.VIN_REFERENCE, src.fault_count, src.max_engine_temp, src.severity_label);

        rows_processed := SQLROWCOUNT;
        RETURN 'Alerts evaluated. New alerts written: ' || rows_processed;
    ELSE
        RETURN 'No new stream data. Skipping.';
    END IF;
END;
$$;

-- ── Step 4: Scheduled Task — Runs Every 15 Minutes ────────────────────────────
CREATE OR REPLACE TASK AI_PROJECT_DB.ALERTS.TASK_FAULT_ALERT
    WAREHOUSE    = DBT_TRANSFORM_WH
    SCHEDULE     = '15 MINUTE'
    COMMENT      = 'Polls GLD_DEALERSHIP_ERRORS stream and writes alerts for high-risk vehicles.'
AS
    CALL AI_PROJECT_DB.ALERTS.SP_EVALUATE_FAULT_ALERTS();

-- Activate the Task (Tasks are created SUSPENDED by default)
ALTER TASK AI_PROJECT_DB.ALERTS.TASK_FAULT_ALERT RESUME;


-- ── Step 5: Verification Queries ──────────────────────────────────────────────

-- Check task is running
SHOW TASKS LIKE 'TASK_FAULT_ALERT' IN SCHEMA AI_PROJECT_DB.ALERTS;

-- Manually trigger for immediate testing (bypasses the 15-min schedule)
-- EXECUTE TASK AI_PROJECT_DB.ALERTS.TASK_FAULT_ALERT;

-- View generated alerts (sorted by severity)
-- SELECT * FROM AI_PROJECT_DB.ALERTS.FAULT_NOTIFICATIONS
-- ORDER BY severity_label DESC, triggered_at DESC
-- LIMIT 20;

-- Check task run history & errors
-- SELECT *
-- FROM TABLE(AI_PROJECT_DB.INFORMATION_SCHEMA.TASK_HISTORY(
--     SCHEDULED_TIME_RANGE_START => DATEADD('hour', -1, CURRENT_TIMESTAMP()),
--     TASK_NAME => 'TASK_FAULT_ALERT'
-- ));
