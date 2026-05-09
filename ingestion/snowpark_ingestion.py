"""
Snowpark Schema-on-Read Ingestion Pipeline
==========================================
Pattern: Land raw JSON as VARIANT in Bronze → flatten known fields in Silver.

WHY THIS MATTERS:
  Old approach: Hard-coded schema breaks when a new sensor is added.
  This approach: Every JSON field lands safely as VARIANT. The Silver dbt model
  then extracts only the fields it cares about using dot-notation. Adding a new
  sensor type = zero pipeline changes; just update the Silver model.

Bronze table structure (BRONZE_TELEMATICS_RAW):
  ┌─────────────────┬────────────┬────────────────────────────────────────────┐
  │ INGESTION_ID    │ RECEIVED_AT│ RAW_PAYLOAD (VARIANT)                      │
  ├─────────────────┼────────────┼────────────────────────────────────────────┤
  │ uuid-abc-123    │ 2026-05-09 │ {"vin":"VIN_001","engine_temp_c":98.5,...} │
  │ uuid-def-456    │ 2026-05-09 │ {"vin":"VIN_002","tire_pressure_psi":32}   │
  └─────────────────┴────────────┴────────────────────────────────────────────┘
"""

import os
import json
import uuid
import logging
from datetime import datetime, UTC
from typing import Any
from dotenv import load_dotenv
from snowflake.snowpark import Session
from snowflake.snowpark.types import StructType, StructField, StringType, TimestampType, VariantType

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SchemaOnReadIngestion")

# ── Bronze target schema ──────────────────────────────────────────────────────
# This schema NEVER changes regardless of payload content. All sensor data
# lands in RAW_PAYLOAD as VARIANT and is parsed downstream by dbt.
BRONZE_SCHEMA = StructType([
    StructField("INGESTION_ID",    StringType(),    nullable=False),
    StructField("SOURCE_FILE",     StringType(),    nullable=False),
    StructField("CLOUD_SOURCE",    StringType(),    nullable=True),
    StructField("RECEIVED_AT",     StringType(),    nullable=False),   # ISO string → cast in SQL
    StructField("RAW_PAYLOAD",     VariantType(),   nullable=False),   # 👈 Schema-on-read
])

BRONZE_TABLE = "STAGING.BRONZE_TELEMATICS_RAW"


# ── Session ───────────────────────────────────────────────────────────────────
def create_snowpark_session() -> Session:
    conn_params = {
        "account":   os.getenv("SNOWFLAKE_ACCOUNT"),
        "user":      os.getenv("SNOWFLAKE_USER"),
        "password":  os.getenv("SNOWFLAKE_PASSWORD"),
        "role":      os.getenv("SNOWFLAKE_ROLE",      "CORTEX_DEV_ROLE"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "DBT_TRANSFORM_WH"),
        "database":  os.getenv("SNOWFLAKE_DATABASE",  "AI_PROJECT_DB"),
        "schema":    os.getenv("SNOWFLAKE_SCHEMA",    "STAGING"),
    }
    logger.info("Creating Snowpark session as role: %s", conn_params["role"])
    return Session.builder.configs(conn_params).create()


# ── Schema-on-Read: Envelope Builder ─────────────────────────────────────────
def _build_envelope(raw_record: dict[str, Any], source_file: str) -> dict[str, Any]:
    """
    Wraps ANY raw JSON record in a fixed outer envelope.
    The inner payload is untouched — all fields preserved regardless of schema.
    """
    return {
        "INGESTION_ID": str(uuid.uuid4()),
        "SOURCE_FILE":  source_file,
        "CLOUD_SOURCE": raw_record.pop("cloud_source", "UNKNOWN"),   # promote & remove from payload
        "RECEIVED_AT":  datetime.now(UTC).isoformat(),
        "RAW_PAYLOAD":  raw_record,   # ← all sensor fields land here, no schema enforcement
    }


# ── Ensure Bronze Landing Table Exists ───────────────────────────────────────
def ensure_bronze_table(session: Session) -> None:
    """
    Creates the VARIANT-based Bronze table if it doesn't exist.
    This is idempotent — safe to run on every pipeline execution.
    """
    session.sql(f"""
        CREATE TABLE IF NOT EXISTS {BRONZE_TABLE} (
            INGESTION_ID   STRING        NOT NULL DEFAULT UUID_STRING(),
            SOURCE_FILE    STRING        NOT NULL,
            CLOUD_SOURCE   STRING,
            RECEIVED_AT    TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
            RAW_PAYLOAD    VARIANT       NOT NULL     -- All sensor data lands here
        )
        DATA_RETENTION_TIME_IN_DAYS = 7              -- Time Travel for rollback
        COMMENT = 'Bronze landing zone — schema-on-read VARIANT store for raw telemetry'
    """).collect()
    logger.info("Bronze table verified: %s", BRONZE_TABLE)


# ── Deduplication Guard ───────────────────────────────────────────────────────
def _already_ingested(session: Session, source_file: str) -> bool:
    """
    Prevents double-ingestion of the same file using the SOURCE_FILE watermark.
    Production pattern: use a separate INGESTION_LOG table or Snowpipe instead.
    """
    result = session.sql(f"""
        SELECT COUNT(1) AS cnt
        FROM {BRONZE_TABLE}
        WHERE SOURCE_FILE = '{source_file}'
    """).collect()
    return result[0]["CNT"] > 0


# ── Core Ingestion ─────────────────────────────────────────────────────────────
def ingest_raw_json_files(session: Session, data_folder: str = "data/raw_cloud_events/") -> int:
    """
    Reads all *.json files from the given folder.
    Each record — regardless of its keys — is wrapped in a fixed envelope and
    written to Bronze as VARIANT. No hard-coded column extraction happens here.

    Returns the number of records written.
    """
    ensure_bronze_table(session)

    envelopes: list[dict] = []
    files_processed = 0

    if not os.path.isdir(data_folder):
        logger.warning("Data folder not found: %s — creating it for demo.", data_folder)
        os.makedirs(data_folder, exist_ok=True)
        _write_demo_payloads(data_folder)

    for filename in sorted(os.listdir(data_folder)):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(data_folder, filename)

        if _already_ingested(session, filename):
            logger.info("Skipping already-ingested file: %s", filename)
            continue

        logger.info("Processing file: %s", filename)
        with open(filepath, "r") as fh:
            raw_records = json.load(fh)

        if isinstance(raw_records, dict):   # single-record files
            raw_records = [raw_records]

        for record in raw_records:
            envelopes.append(_build_envelope(record, source_file=filename))

        files_processed += 1

    if not envelopes:
        logger.info("Nothing new to ingest.")
        return 0

    # ── Write to Snowflake ── ─────────────────────────────────────────────────
    # VARIANT columns must be serialised to JSON strings for the Snowpark writer.
    # Snowflake automatically parses them back to VARIANT on ingest.
    serialised = [
        (
            row["INGESTION_ID"],
            row["SOURCE_FILE"],
            row["CLOUD_SOURCE"],
            row["RECEIVED_AT"],
            json.dumps(row["RAW_PAYLOAD"]),   # ← VARIANT serialisation
        )
        for row in envelopes
    ]

    df = session.create_dataframe(serialised, schema=BRONZE_SCHEMA)
    df.write.mode("append").save_as_table(BRONZE_TABLE)

    logger.info(
        "✅ Wrote %d records from %d file(s) → %s",
        len(envelopes), files_processed, BRONZE_TABLE
    )
    return len(envelopes)


# ── Demo Payload Generator ────────────────────────────────────────────────────
def _write_demo_payloads(folder: str) -> None:
    """
    Creates realistic demo JSON files with DIFFERENT schemas to prove
    schema-on-read works when new sensor types appear mid-pipeline.
    """
    # Gen-1 sensor payload (original 3 fields)
    gen1 = [
        {"vin": "VIN_001", "engine_temp_c": 98.5,  "error_code": "P0300", "cloud_source": "AWS"},
        {"vin": "VIN_002", "engine_temp_c": 110.2, "error_code": "NONE",  "cloud_source": "AWS"},
    ]
    # Gen-2 sensor payload — NEW fields: tire_pressure_psi, battery_voltage_v, gps_lat, gps_lon
    gen2 = [
        {
            "vin": "VIN_003", "engine_temp_c": 95.0, "error_code": "P0171",
            "tire_pressure_psi": {"FL": 32.1, "FR": 31.8, "RL": 33.0, "RR": 32.5},
            "battery_voltage_v": 12.6,
            "cloud_source": "AZURE"
        },
    ]
    # Gen-3 sensor payload — ANOTHER new field: adas_event (an object)
    gen3 = [
        {
            "vin": "VIN_004", "engine_temp_c": 88.0, "error_code": "NONE",
            "adas_event": {"type": "LANE_DEPARTURE", "severity": "LOW", "timestamp_ms": 1746796033000},
            "cloud_source": "AWS",
            "log_text": "Driver approached highway on-ramp. Lane keep assist engaged."
        },
    ]
    with open(os.path.join(folder, "gen1_telemetry.json"), "w") as f: json.dump(gen1, f, indent=2)
    with open(os.path.join(folder, "gen2_telemetry.json"), "w") as f: json.dump(gen2, f, indent=2)
    with open(os.path.join(folder, "gen3_telemetry.json"), "w") as f: json.dump(gen3, f, indent=2)
    logger.info("Demo payloads written to %s", folder)


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    session = create_snowpark_session()
    records_written = ingest_raw_json_files(session)
    logger.info("Pipeline complete. Total records written: %d", records_written)
