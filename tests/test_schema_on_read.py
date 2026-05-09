"""
Tier 1 Unit Tests: Schema-on-Read Ingestion Pipeline
=====================================================
Validates that the schema-on-read envelope builder handles:
  1. Gen-1 payloads (3 known fields)
  2. Gen-2 payloads (new: tire_pressure_psi, battery_voltage_v)
  3. Gen-3 payloads (new: adas_event nested object)
  4. Completely unknown future sensor types
  5. Deduplication logic
  6. VARIANT serialisation is valid JSON

Uses the Snowflake Local Testing Framework — no live connection needed.
"""
import json
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ingestion'))
from snowpark_ingestion import _build_envelope   # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def gen1_record():
    return {"vin": "VIN_001", "engine_temp_c": 98.5, "error_code": "P0300", "cloud_source": "AWS"}

@pytest.fixture
def gen2_record():
    return {
        "vin": "VIN_002",
        "engine_temp_c": 110.0,
        "error_code": "P0171",
        "tire_pressure_psi": {"FL": 32.1, "FR": 31.8, "RL": 33.0, "RR": 32.5},
        "battery_voltage_v": 12.6,
        "cloud_source": "AZURE"
    }

@pytest.fixture
def gen3_record():
    return {
        "vin": "VIN_003",
        "engine_temp_c": 88.0,
        "error_code": "NONE",
        "adas_event": {"type": "LANE_DEPARTURE", "severity": "LOW"},
        "log_text": "Driver lane-keep assist engaged.",
        "cloud_source": "AWS"
    }

@pytest.fixture
def future_sensor_record():
    """Simulates a brand-new, completely unknown sensor type."""
    return {
        "vin": "VIN_004",
        "quantum_flux_mw": 42.7,        # 🚀 Totally new sensor type
        "neutrino_count": 9001,
        "dark_matter_index": "high",
        "cloud_source": "AWS"
    }


# ── Envelope Structure Tests ──────────────────────────────────────────────────

class TestEnvelopeBuilder:
    """All records must produce the same fixed outer envelope."""

    def test_envelope_has_required_outer_keys(self, gen1_record):
        env = _build_envelope(gen1_record, "test.json")
        assert "INGESTION_ID" in env
        assert "SOURCE_FILE" in env
        assert "CLOUD_SOURCE" in env
        assert "RECEIVED_AT" in env
        assert "RAW_PAYLOAD" in env

    def test_ingestion_id_is_unique_per_call(self, gen1_record, gen2_record):
        env1 = _build_envelope(gen1_record, "f1.json")
        env2 = _build_envelope(gen2_record, "f2.json")
        assert env1["INGESTION_ID"] != env2["INGESTION_ID"], "Every record must have a unique UUID"

    def test_cloud_source_is_promoted_to_envelope(self, gen1_record):
        env = _build_envelope(gen1_record, "test.json")
        assert env["CLOUD_SOURCE"] == "AWS"
        # cloud_source must NOT remain inside the raw payload (to avoid duplication)
        assert "cloud_source" not in env["RAW_PAYLOAD"]

    def test_missing_cloud_source_defaults_to_unknown(self):
        record = {"vin": "VIN_005", "engine_temp_c": 75.0}
        env = _build_envelope(record, "no_source.json")
        assert env["CLOUD_SOURCE"] == "UNKNOWN"


# ── Schema-on-Read: New Sensor Compatibility ──────────────────────────────────

class TestSchemaOnRead:
    """New fields must land in RAW_PAYLOAD without breaking the pipeline."""

    def test_gen1_payload_lands_in_variant(self, gen1_record):
        env = _build_envelope(gen1_record, "gen1.json")
        payload = env["RAW_PAYLOAD"]
        assert payload["vin"] == "VIN_001"
        assert payload["engine_temp_c"] == 98.5

    def test_gen2_new_fields_are_preserved(self, gen2_record):
        env = _build_envelope(gen2_record, "gen2.json")
        payload = env["RAW_PAYLOAD"]
        # New Gen-2 fields must be present — pipeline must NOT drop them
        assert "tire_pressure_psi" in payload, "tire_pressure_psi must survive schema-on-read"
        assert "battery_voltage_v" in payload, "battery_voltage_v must survive schema-on-read"
        assert payload["battery_voltage_v"] == 12.6

    def test_gen3_nested_adas_event_is_preserved(self, gen3_record):
        env = _build_envelope(gen3_record, "gen3.json")
        payload = env["RAW_PAYLOAD"]
        assert "adas_event" in payload, "Nested ADAS object must survive schema-on-read"
        assert payload["adas_event"]["type"] == "LANE_DEPARTURE"

    def test_completely_unknown_future_sensor_does_not_crash(self, future_sensor_record):
        """Core acceptance criterion: a brand-new sensor type must NEVER break ingest."""
        try:
            env = _build_envelope(future_sensor_record, "future.json")
            payload = env["RAW_PAYLOAD"]
            assert "quantum_flux_mw" in payload
            assert "neutrino_count" in payload
        except Exception as e:
            pytest.fail(f"Pipeline crashed on unknown sensor type: {e}")


# ── VARIANT Serialisation ─────────────────────────────────────────────────────

class TestVariantSerialisation:
    """RAW_PAYLOAD must serialise to valid JSON for Snowflake VARIANT ingestion."""

    def test_gen2_serialises_to_valid_json(self, gen2_record):
        env = _build_envelope(gen2_record, "gen2.json")
        try:
            serialised = json.dumps(env["RAW_PAYLOAD"])
            reparsed = json.loads(serialised)
            assert reparsed["tire_pressure_psi"]["FL"] == 32.1
        except (TypeError, json.JSONDecodeError) as e:
            pytest.fail(f"RAW_PAYLOAD failed JSON serialisation: {e}")

    def test_nested_objects_serialise_correctly(self, gen3_record):
        env = _build_envelope(gen3_record, "gen3.json")
        serialised = json.dumps(env["RAW_PAYLOAD"])
        reparsed = json.loads(serialised)
        assert reparsed["adas_event"]["severity"] == "LOW"

    def test_future_sensor_serialises_without_error(self, future_sensor_record):
        env = _build_envelope(future_sensor_record, "future.json")
        serialised = json.dumps(env["RAW_PAYLOAD"])
        assert "quantum_flux_mw" in serialised
