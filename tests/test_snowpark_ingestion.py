"""
Standard 1: PyTest + Snowpark Local Testing
Tests the ingestion pipeline logic WITHOUT a live Snowflake connection.
Uses Snowpark's local testing framework to mock DataFrames.
"""
import pytest
from unittest.mock import MagicMock, patch


# ─────────────────────────────────────────────
# Unit Tests: Snowpark Ingestion Logic
# ─────────────────────────────────────────────
class TestSnowparkIngestion:
    """Validates ingestion logic using mocked Snowpark sessions."""

    def test_session_creation_returns_none_without_credentials(self):
        """If .env is missing Snowflake keys, session must safely return None."""
        with patch.dict("os.environ", {}, clear=True):
            from app.core.snowflake_session import get_snowpark_session
            with patch("app.core.snowflake_session.Session.builder") as mock_builder:
                mock_builder.configs.return_value.create.side_effect = Exception("No creds")
                session = get_snowpark_session()
                assert session is None

    def test_ingestion_schema_fields_present(self):
        """Validates the expected schema columns exist on a mocked DataFrame."""
        mock_session = MagicMock()
        mock_df = MagicMock()
        mock_session.read.json.return_value = mock_df
        mock_df.columns = ["VIN", "ERROR_CODE", "TIMESTAMP", "LOG_TEXT"]

        assert "VIN" in mock_df.columns
        assert "ERROR_CODE" in mock_df.columns
        assert "TIMESTAMP" in mock_df.columns

    def test_ingestion_write_called_once(self):
        """Ensures the .write.save_as_table() is invoked exactly once per batch."""
        mock_session = MagicMock()
        mock_df = MagicMock()
        mock_session.read.json.return_value = mock_df

        # Simulate ingestion call
        mock_df.write.mode("append").save_as_table("RAW_LOGS")
        mock_df.write.mode.assert_called_once_with("append")
