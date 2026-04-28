"""
conftest.py — Shared PyTest Fixtures for the Automotive Copilot Test Suite
===========================================================================

Tier 1: Snowflake Local Testing Framework
Uses `Session.builder.config("local_testing", True)` to spin up an in-process
Snowflake emulator — zero cloud cost, zero network calls.

This fixture is available to ALL test files automatically via PyTest's
fixture injection system.
"""
import pytest
from snowflake.snowpark import Session


@pytest.fixture(scope="session")
def snowpark_local_session():
    """
    Creates a single Snowflake Local Testing session for the entire test run.

    scope="session" means it's created ONCE and reused across all tests —
    the same pattern used in enterprise Snowpark test suites.

    What this emulates (without a live Snowflake connection):
    - DataFrame creation & schema validation
    - SQL SELECT, FILTER, GROUP BY, JOIN operations
    - write.mode("append").save_as_table() calls
    - VECTOR operations (limited support in emulator)
    """
    session = (
        Session.builder
        .config("local_testing", True)
        .create()
    )
    yield session
    session.close()


@pytest.fixture(scope="function")
def sample_diagnostic_log_df(snowpark_local_session):
    """
    Returns a Snowpark DataFrame mimicking the RAW_LOGS Snowflake table structure.
    Used for testing Bronze-layer ingestion logic locally.
    """
    from snowflake.snowpark.types import StructType, StructField, StringType, FloatType, TimestampType
    import datetime

    schema = StructType([
        StructField("VIN",                 StringType()),
        StructField("ERROR_CODE",          StringType()),
        StructField("ENGINE_TEMP_CELSIUS", FloatType()),
        StructField("LOG_TEXT",            StringType()),
        StructField("RECORDED_AT",         StringType()),
    ])

    data = [
        ("VIN_AWS_001", "P0300", 98.5,  "Misfire detected on cylinder 3",    "2026-04-24 10:00:00"),
        ("VIN_AWS_001", "P0420", 101.2, "Catalyst efficiency below threshold","2026-04-24 10:05:00"),
        ("VIN_AZURE_002", "P0217", 125.0, "Engine overheat condition",        "2026-04-24 11:00:00"),
        ("VIN_AZURE_002", None,    99.1, "Normal operation cycle",            "2026-04-24 11:30:00"),
        ("VIN_AWS_003",   "P0128", 78.3, "Coolant temp below thermostat",     "2026-04-24 12:00:00"),
    ]

    return snowpark_local_session.create_dataframe(data, schema=schema)
