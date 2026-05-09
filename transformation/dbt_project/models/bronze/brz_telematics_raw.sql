{{ config(materialized='view') }}

-- =========================================================================
-- BRONZE LAYER: Schema-on-Read Flattening
-- Source: BRONZE_TELEMATICS_RAW (VARIANT column — any JSON shape lands here)
--
-- Pattern: Extract KNOWN fields with dot-notation coercion.
--          UNKNOWN / future fields remain accessible via RAW_PAYLOAD['field']
--          without requiring any pipeline or model change.
-- =========================================================================

WITH raw AS (
    SELECT *
    FROM AI_PROJECT_DB.STAGING.BRONZE_TELEMATICS_RAW
    WHERE RAW_PAYLOAD IS NOT NULL
)

SELECT
    INGESTION_ID,
    SOURCE_FILE,
    CLOUD_SOURCE,
    RECEIVED_AT,

    -- ── Known Core Fields (dot-notation coercion) ────────────────────────
    RAW_PAYLOAD['vin']::STRING               AS vin,
    RAW_PAYLOAD['error_code']::STRING        AS error_code,
    RAW_PAYLOAD['engine_temp_c']::FLOAT      AS engine_temperature_celsius,
    RAW_PAYLOAD['log_text']::STRING          AS log_text,

    -- ── Gen-2 Fields: Tire Pressure (nested object → VARIANT) ────────────
    RAW_PAYLOAD['tire_pressure_psi']         AS tire_pressure_psi_variant,

    -- ── Gen-2 Fields: Battery ─────────────────────────────────────────────
    RAW_PAYLOAD['battery_voltage_v']::FLOAT  AS battery_voltage_v,

    -- ── Gen-3 Fields: ADAS Event (new sensor type, zero pipeline change) ──
    RAW_PAYLOAD['adas_event']                AS adas_event_variant,
    RAW_PAYLOAD['adas_event']['type']::STRING    AS adas_event_type,
    RAW_PAYLOAD['adas_event']['severity']::STRING AS adas_event_severity,

    -- ── Escape Hatch: Full raw payload always available ───────────────────
    -- Analysts can query RAW_PAYLOAD['any_future_field'] without a deploy.
    RAW_PAYLOAD                              AS raw_payload

FROM raw
