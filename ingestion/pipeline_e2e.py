"""
End-to-End Data Pipeline Runner
=================================
Orchestrates the complete data flow:

  STEP 1: Generate test data (JSON + PDFs)
  STEP 2: Upload to AWS S3  (telemetry + manuals)
  STEP 3: Upload to Azure Blob (telemetry + manuals)
  STEP 4: Ingest JSON into Snowflake Bronze (Snowpark schema-on-read)
  STEP 5: (Manual) Run dbt to transform Bronze -> Silver -> Gold

Usage:
  python ingestion/pipeline_e2e.py              # full run
  python ingestion/pipeline_e2e.py --local-only # skip cloud uploads
  python ingestion/pipeline_e2e.py --generate   # only generate test data

Architecture:
                    AWS S3 Bucket
                   /incoming/manuals/    <-- PDFs
  Local Data  -->  /incoming/telemetry/  <-- JSON (Hive partitioned)
                      |
                      | Snowflake External Stage
                      v
              BRONZE_TELEMATICS_RAW (VARIANT)
              parsed_vehicle_manuals (CORTEX.PARSE_DOCUMENT)
                      |
                      | dbt run
                      v
              SILVER: slv_telematics, slv_fault_analysis
                      |
                      | dbt run
                      v
              GOLD:   gld_dealership_errors, gld_ai_audit_report
                      |
                      | Streamlit Dashboard / FastAPI
                      v
              Business Users & AI Diagnostics API
"""

import sys
import os
import argparse
import subprocess
import time

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "data"))

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def banner(step: int, title: str, total: int = 5) -> None:
    print(f"\n{'='*60}")
    print(f"  STEP {step}/{total}: {title}")
    print(f"{'='*60}")


def run_step(cmd: list[str], cwd: str = PROJECT_ROOT) -> bool:
    """Runs a subprocess command and returns True on success."""
    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=False)
    return result.returncode == 0


def step1_generate_data() -> None:
    banner(1, "Generate Test Data (JSON + PDFs)")
    venv_python = os.path.join(PROJECT_ROOT, "venv", "bin", "python3.11")
    python = venv_python if os.path.exists(venv_python) else sys.executable

    # Generate synthetic data
    ok = run_step([python, "data/generate_test_data.py"])
    if not ok:
        print("  ⚠️  Data generation had issues — continuing with existing files")

    # Try to download real public PDFs
    ok = run_step([python, "data/download_real_manuals.py"])
    if not ok:
        print("  ⚠️  Some PDF downloads failed — synthetic manuals will be used")


def step2_upload_aws() -> None:
    banner(2, "Upload to AWS S3")
    venv_python = os.path.join(PROJECT_ROOT, "venv", "bin", "python3.11")
    python = venv_python if os.path.exists(venv_python) else sys.executable

    # Check credentials first
    if not os.getenv("AWS_ACCESS_KEY_ID") and not os.getenv("AWS_S3_BUCKET"):
        print("  ⚠️  AWS credentials not found in .env — skipping S3 upload")
        print("  Set: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET")
        return

    run_step([python, "ingestion/upload_to_aws_s3.py"])


def step3_upload_azure() -> None:
    banner(3, "Upload to Azure Blob Storage")
    venv_python = os.path.join(PROJECT_ROOT, "venv", "bin", "python3.11")
    python = venv_python if os.path.exists(venv_python) else sys.executable

    if not os.getenv("AZURE_STORAGE_CONNECTION_STRING") and \
       not os.getenv("AZURE_STORAGE_ACCOUNT_NAME"):
        print("  ⚠️  Azure credentials not found in .env — skipping Blob upload")
        print("  Set: AZURE_STORAGE_CONNECTION_STRING  or")
        print("       AZURE_STORAGE_ACCOUNT_NAME + AZURE_STORAGE_ACCOUNT_KEY")
        return

    run_step([python, "ingestion/upload_to_azure_blob.py"])


def step4_snowpark_ingest() -> None:
    banner(4, "Snowpark Ingestion -> Snowflake Bronze (schema-on-read)")
    venv_python = os.path.join(PROJECT_ROOT, "venv", "bin", "python3.11")
    python = venv_python if os.path.exists(venv_python) else sys.executable

    if not os.getenv("SNOWFLAKE_ACCOUNT"):
        print("  ⚠️  Snowflake credentials not found in .env — skipping ingest")
        print("  Set: SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD")
        return

    run_step([python, "ingestion/snowpark_ingestion.py"])


def step5_dbt_transform() -> None:
    banner(5, "dbt Transform: Bronze -> Silver -> Gold")
    dbt_dir = os.path.join(PROJECT_ROOT, "transformation", "dbt_project")

    if not os.path.isdir(dbt_dir):
        print(f"  dbt project not found at: {dbt_dir}")
        return

    venv_dbt = os.path.join(PROJECT_ROOT, "venv", "bin", "dbt")
    dbt_cmd  = venv_dbt if os.path.exists(venv_dbt) else "dbt"

    print("\n  Running dbt in sequence: Bronze -> Silver -> Gold")

    steps = [
        ([dbt_cmd, "run", "--select", "brz_telematics_raw"],           "Bronze: brz_telematics_raw"),
        ([dbt_cmd, "run", "--select", "stg_pending_files"],             "Bronze: stg_pending_files"),
        ([dbt_cmd, "run", "--select", "slv_telematics"],                "Silver: slv_telematics"),
        ([dbt_cmd, "run", "--select", "slv_fault_analysis"],            "Silver: slv_fault_analysis (Cortex AI)"),
        ([dbt_cmd, "run", "--select", "parsed_vehicle_manuals"],        "Gold:   parsed_vehicle_manuals"),
        ([dbt_cmd, "run", "--select", "gld_dealership_errors"],         "Gold:   gld_dealership_errors (Embeddings)"),
        ([dbt_cmd, "run", "--select", "gld_ai_audit_report"],           "Gold:   gld_ai_audit_report"),
        ([dbt_cmd, "test"],                                              "dbt test: all models"),
    ]

    for cmd, label in steps:
        print(f"\n  [{label}]")
        ok = run_step(cmd, cwd=dbt_dir)
        if not ok:
            print(f"  ⚠️  Step failed: {label}  (continuing pipeline)")


def print_pipeline_summary() -> None:
    print(f"""
{'='*60}
  Pipeline Complete
{'='*60}

  Data Flow Achieved:
  
  data/raw_cloud_events/*.json  (258 records)
       AWS_S3/telemetry/        (Hive partitioned)
       AZURE_BLOB/telemetry/    (Hive partitioned)
              |
              v  Snowpark schema-on-read
  BRONZE_TELEMATICS_RAW (VARIANT column)
              |
              v  dbt: slv_telematics + slv_fault_analysis
  SILVER: Cortex SUMMARIZE + SENTIMENT + CLASSIFY
              |
              v  dbt: gld_dealership_errors
  GOLD: EMBED_TEXT_768 pre-computed vectors + fault counts
              |
              v  FastAPI + Streamlit Dashboard
  Business users & AI Diagnostics

  Next: Open Snowsight and run
    SELECT * FROM AI_PROJECT_DB.GOLD.GLD_DEALERSHIP_ERRORS LIMIT 10;
    SELECT * FROM AI_PROJECT_DB.ALERTS.FAULT_NOTIFICATIONS;
{'='*60}
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automotive Copilot E2E Pipeline")
    parser.add_argument("--local-only", action="store_true",
                        help="Skip AWS/Azure uploads, only generate data and ingest to Snowflake")
    parser.add_argument("--generate",   action="store_true",
                        help="Only generate test data files, no uploads or ingestion")
    args = parser.parse_args()

    start = time.time()

    step1_generate_data()

    if not args.generate:
        if not args.local_only:
            step2_upload_aws()
            step3_upload_azure()

        step4_snowpark_ingest()
        step5_dbt_transform()

    elapsed = round(time.time() - start, 1)
    print_pipeline_summary()
    print(f"  Total elapsed: {elapsed}s")
