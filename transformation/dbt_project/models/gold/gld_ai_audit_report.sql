{{ config(materialized='table') }}

-- GOLD LAYER: AI Audit Report Table
-- Stores structured JSON output from the Cortex Diagnostic Engine.
-- This model is the Source of Truth for AI output quality evaluation.

WITH raw_ai_responses AS (
    SELECT
        vin_reference,
        diagnostic_question,
        ai_response_json,   -- VARIANT column: structured JSON from CORTEX.COMPLETE
        confidence_score,
        CURRENT_TIMESTAMP() AS evaluated_at
    FROM {{ ref('slv_telematics') }}
    WHERE ai_response_json IS NOT NULL
)

SELECT
    vin_reference,
    diagnostic_question,
    ai_response_json,
    confidence_score,
    evaluated_at,
    -- Extract key fields from the VARIANT for easy querying
    ai_response_json:diagnosis::STRING          AS parsed_diagnosis,
    ai_response_json:confidence_score::FLOAT    AS parsed_confidence,
    ai_response_json:supporting_evidence::STRING AS parsed_evidence
FROM raw_ai_responses
