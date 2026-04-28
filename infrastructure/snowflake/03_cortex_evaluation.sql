-- ============================================================
-- Tier 3: Cortex Agent Evaluation — Ground Truth Setup
-- Standard: One LLM grades another LLM's output (2026 pattern)
-- Run this ONCE in Snowflake to set up the evaluation infrastructure.
-- ============================================================

USE ROLE CORTEX_DEV_ROLE;
USE DATABASE AI_PROJECT_DB;
USE SCHEMA STAGING;

-- Step 1: Create the Ground Truth Table
-- This is the "Answer Key" your CI/CD pipeline evaluates against.
CREATE OR REPLACE TABLE AI_EVAL_DATA (
    eval_id         NUMBER AUTOINCREMENT PRIMARY KEY,
    input_query     STRING  NOT NULL,
    vin_context     STRING,
    error_code      STRING,
    expected_answer STRING  NOT NULL,   -- The "perfect" answer written by a domain expert
    category        STRING              -- "critical", "safety", "maintenance"
);

-- Step 2: Populate with Automotive Expert Ground Truth
INSERT INTO AI_EVAL_DATA (input_query, vin_context, error_code, expected_answer, category)
VALUES
(
    'Engine is misfiring on cold start with rough idle',
    'VIN_AWS_001',
    'P0300',
    'The P0300 code indicates a random/multiple cylinder misfire. During cold start, '
    'this is commonly caused by worn spark plugs, a faulty ignition coil, or low '
    'compression. Recommended action: Inspect cylinder-specific coil packs and replace '
    'spark plugs every 30,000 miles. Acceptance criteria: Misfire count < 2 per 1000 cycles.',
    'critical'
),
(
    'Coolant temperature warning light illuminated, steam from hood',
    'VIN_AZURE_002',
    'P0217',
    'P0217 indicates engine overtemperature condition. Immediate action required: '
    'Stop the vehicle and allow cooling. Check coolant reservoir level and radiator '
    'for leaks. Inspect water pump belt tension. '
    'Acceptance criteria: Coolant temp stabilizes below 100°C within 15 minutes.',
    'safety'
),
(
    'Oil pressure warning light on with engine knocking',
    'VIN_AWS_003',
    NULL,
    'Low oil pressure with engine knock indicates potential bearing failure or oil '
    'pump malfunction. Do not continue driving. Check oil level and quality immediately. '
    'If oil level is normal, disable vehicle and tow to service. '
    'Acceptance criteria: Oil pressure reads 25-65 PSI at operating temperature.',
    'critical'
),
(
    'How do I reset the oil maintenance reminder light?',
    NULL,
    NULL,
    'To reset the oil maintenance light: Turn the ignition to ON without starting. '
    'Press the accelerator pedal to the floor 3 times within 5 seconds. '
    'Turn the ignition off. The light should extinguish on next startup. '
    'Acceptance criteria: Maintenance indicator no longer illuminated after reset.',
    'maintenance'
);

-- ============================================================
-- Step 3: Create Snowflake Stage for Eval Config
-- ============================================================
CREATE STAGE IF NOT EXISTS PROJECT_STAGE
    COMMENT = 'Stores evaluation config YAML files for CORTEX.EVALUATE';

-- ============================================================
-- Step 4: Run Cortex Evaluation (Post-Deployment CI/CD Step)
-- NOTE: SNOWFLAKE.ML.EXECUTE_AI_EVALUATION is in Controlled Availability.
-- Use CORTEX.EVALUATE as the GA alternative.
-- ============================================================

-- Faithfulness + Relevance evaluation using CORTEX.EVALUATE
-- This runs *after* your API has generated responses and stored them
-- in the gld_ai_audit_report table.
CREATE OR REPLACE TABLE AI_EVAL_RESULTS AS
SELECT
    e.eval_id,
    e.input_query,
    e.expected_answer,
    r.parsed_diagnosis   AS actual_answer,
    r.confidence_score,

    -- CORTEX.EVALUATE: Grades faithfulness (did the AI hallucinate?)
    SNOWFLAKE.CORTEX.COMPLETE(
        'mistral-large2',
        CONCAT(
            'You are an AI evaluation judge. Score the answer from 0.0 to 1.0 for FAITHFULNESS. ',
            'Question: ', e.input_query,
            ' Expected Answer: ', e.expected_answer,
            ' AI Answer: ', r.parsed_diagnosis,
            ' Return ONLY a JSON: {"faithfulness": <score>, "reason": "<one sentence>"}'
        )
    )::VARIANT AS faithfulness_eval,

    -- Extract the numeric score
    faithfulness_eval:faithfulness::FLOAT AS faithfulness_score

FROM AI_EVAL_DATA e
LEFT JOIN AI_PROJECT_DB.DBT_MODELS.GLD_AI_AUDIT_REPORT r
    ON e.vin_context = r.vin_reference;

-- ============================================================
-- Step 5: CI/CD Quality Gate Query
-- Returns exit signal: 0 = PASS, 1 = FAIL
-- This is what your pipeline executes to gate the deployment.
-- ============================================================
SELECT
    COUNT(*)                                    AS total_evaluations,
    ROUND(AVG(faithfulness_score), 3)           AS avg_faithfulness,
    ROUND(MIN(faithfulness_score), 3)           AS min_faithfulness,
    CASE
        WHEN AVG(faithfulness_score) >= 0.80 THEN 'PASS — Deploy Approved'
        ELSE 'FAIL — Accuracy below 80% SLA. Deployment BLOCKED.'
    END                                         AS deployment_gate_status
FROM AI_EVAL_RESULTS;
