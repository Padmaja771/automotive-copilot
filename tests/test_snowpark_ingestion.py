"""
Tier 1: Snowpark Local Testing — Ingestion Pipeline Unit Tests
==============================================================
Standard: Uses the Snowflake Local Testing Framework (NOT mocks).
Session is injected via conftest.py — no live Snowflake connection needed.

These tests validate the LOGIC of your ingestion and transformation
pipeline code using the Snowflake in-process emulator.
"""
import pytest
from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, count, max as sf_max, when


class TestSnowparkLocalIngestion:
    """
    Validates Bronze-layer ingestion logic using the Snowflake Local Testing Framework.
    Injected fixture: `sample_diagnostic_log_df` from conftest.py
    """

    def test_local_session_is_created(self, snowpark_local_session):
        """Validates that the local testing session starts without a live connection."""
        assert snowpark_local_session is not None
        assert isinstance(snowpark_local_session, Session)

    def test_dataframe_schema_matches_raw_logs_table(self, sample_diagnostic_log_df):
        """Validates that ingested data matches the expected RAW_LOGS schema."""
        schema_fields = {f.name for f in sample_diagnostic_log_df.schema.fields}
        expected_fields = {"VIN", "ERROR_CODE", "ENGINE_TEMP_CELSIUS", "LOG_TEXT", "RECORDED_AT"}
        assert expected_fields == schema_fields, (
            f"Schema mismatch. Expected: {expected_fields}, Got: {schema_fields}"
        )

    def test_row_count_matches_ingestion_batch(self, sample_diagnostic_log_df):
        """Validates the DataFrame contains the correct number of rows for the batch."""
        row_count = sample_diagnostic_log_df.count()
        assert row_count == 5, f"Expected 5 rows from the test batch, got {row_count}"

    def test_filter_by_vin_returns_correct_rows(self, sample_diagnostic_log_df):
        """Validates VIN-based filtering — mimics the RAG retriever's WHERE clause."""
        vin_df = sample_diagnostic_log_df.filter(col("VIN") == "VIN_AWS_001")
        assert vin_df.count() == 2, "VIN_AWS_001 should have 2 diagnostic records."

    def test_critical_temperature_filter(self, sample_diagnostic_log_df):
        """Validates Silver-layer transformation: filter engine temps above 110°C."""
        critical_df = sample_diagnostic_log_df.filter(
            col("ENGINE_TEMP_CELSIUS") > 110.0
        )
        # Only VIN_AZURE_002 has a temp of 125°C
        assert critical_df.count() == 1
        row = critical_df.collect()[0]
        assert row["VIN"] == "VIN_AZURE_002"
        assert row["ENGINE_TEMP_CELSIUS"] == 125.0

    def test_gold_layer_aggregation_logic(self, sample_diagnostic_log_df):
        """
        Validates Gold-layer aggregation — mimics gld_dealership_errors.sql logic:
        GROUP BY vin_reference, COUNT errors, MAX temperature.
        """
        gold_df = (
            sample_diagnostic_log_df
            .filter(col("ERROR_CODE").isNotNull())
            .group_by("VIN")
            .agg(
                count("ERROR_CODE").alias("TOTAL_CRITICAL_ERRORS"),
                sf_max("ENGINE_TEMP_CELSIUS").alias("MAX_ENGINE_TEMP_RECORDED"),
            )
        )

        rows = {r["VIN"]: r for r in gold_df.collect()}

        # VIN_AWS_001: 2 errors  (P0300 + P0420)
        assert rows["VIN_AWS_001"]["TOTAL_CRITICAL_ERRORS"] == 2
        assert rows["VIN_AWS_001"]["MAX_ENGINE_TEMP_RECORDED"] == pytest.approx(101.2, abs=0.1)

        # VIN_AZURE_002: 1 error (P0217 — the null row is excluded)
        assert rows["VIN_AZURE_002"]["TOTAL_CRITICAL_ERRORS"] == 1
        assert rows["VIN_AZURE_002"]["MAX_ENGINE_TEMP_RECORDED"] == pytest.approx(125.0, abs=0.1)

    def test_null_error_code_rows_excluded_in_gold(self, sample_diagnostic_log_df):
        """Validates that NULL error codes are excluded from Gold aggregation (data quality)."""
        gold_df = sample_diagnostic_log_df.filter(col("ERROR_CODE").isNotNull())
        # Row 4 (VIN_AZURE_002, None error) should be excluded
        null_rows = gold_df.filter(col("VIN") == "VIN_AZURE_002").count()
        assert null_rows == 1, (
            "Only 1 non-null error row should remain for VIN_AZURE_002 after filtering."
        )

    def test_write_save_as_table_executes_without_error(
        self, snowpark_local_session, sample_diagnostic_log_df
    ):
        """
        Validates that .write.mode('append').save_as_table() succeeds locally.
        In the Local Testing Framework, this writes to an in-memory table emulator.
        """
        # This should NOT raise an exception
        sample_diagnostic_log_df.write.mode("append").save_as_table("LOCAL_RAW_LOGS")

        # Verify the data was written by reading it back
        result = snowpark_local_session.table("LOCAL_RAW_LOGS")
        assert result.count() == 5, "All 5 rows should be persisted in the local emulator."
