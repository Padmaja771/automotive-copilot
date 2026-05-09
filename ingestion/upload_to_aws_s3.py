"""
AWS S3 Upload — Telemetry JSON + Vehicle Manual PDFs
======================================================
Simulates files arriving from upstream systems into the automotive
data lake on S3. This is the "source" side of the pipeline:

  Local files
      │
      ▼
  AWS S3 Bucket
  ├── incoming/manuals/   ← vehicle PDFs (for Cortex PARSE_DOCUMENT)
  └── incoming/telemetry/ ← JSON events (per cloud source + date)
      ├── source=AWS_S3/date=2026-05-09/aws_gen1_ford_toyota.json
      └── source=AZURE_BLOB/date=2026-05-09/azure_gen3_tesla_tacoma.json

Run:  python ingestion/upload_to_aws_s3.py
Requires: pip install boto3
          AWS credentials in ~/.aws/credentials OR environment variables
          AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
"""

import os
import sys
import json
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime, UTC
from dotenv import load_dotenv

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
S3_BUCKET       = os.getenv("AWS_S3_BUCKET", "automotive-copilot-vehicle-docs-dev")
S3_REGION       = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
LOCAL_ROOT      = os.path.join(os.path.dirname(__file__), "..", "data")
TELEMETRY_DIR   = os.path.join(LOCAL_ROOT, "raw_cloud_events")
MANUALS_DIR     = os.path.join(LOCAL_ROOT, "raw_manuals")
TODAY           = datetime.now(UTC).strftime("%Y-%m-%d")


def get_s3_client():
    """Returns an authenticated S3 client."""
    try:
        client = boto3.client(
            "s3",
            region_name=S3_REGION,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        # Validate credentials with a lightweight call
        client.list_buckets()
        print(f"Connected to AWS S3 (region: {S3_REGION})")
        return client
    except NoCredentialsError:
        print("ERROR: AWS credentials not found.")
        print("  Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your .env file")
        print("  or configure ~/.aws/credentials")
        sys.exit(1)
    except ClientError as e:
        print(f"AWS connection error: {e}")
        sys.exit(1)


def ensure_bucket_exists(s3: boto3.client) -> None:
    """Creates the S3 bucket if it doesn't exist."""
    try:
        s3.head_bucket(Bucket=S3_BUCKET)
        print(f"Bucket exists: s3://{S3_BUCKET}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            print(f"Creating bucket: s3://{S3_BUCKET}")
            if S3_REGION == "us-east-1":
                s3.create_bucket(Bucket=S3_BUCKET)
            else:
                s3.create_bucket(
                    Bucket=S3_BUCKET,
                    CreateBucketConfiguration={"LocationConstraint": S3_REGION}
                )
        else:
            raise


def upload_file(s3: boto3.client, local_path: str, s3_key: str,
                content_type: str = "application/octet-stream") -> bool:
    """Uploads a single file to S3. Returns True on success."""
    try:
        file_size = os.path.getsize(local_path)
        s3.upload_file(
            local_path,
            S3_BUCKET,
            s3_key,
            ExtraArgs={
                "ContentType": content_type,
                "Metadata": {
                    "uploaded-by":    "automotive-copilot-pipeline",
                    "upload-date":    TODAY,
                    "pipeline-stage": "raw-ingestion",
                }
            }
        )
        print(f"  UPLOADED  s3://{S3_BUCKET}/{s3_key}  ({file_size // 1024} KB)")
        return True
    except ClientError as e:
        print(f"  FAILED    {os.path.basename(local_path)}: {e}")
        return False


def upload_vehicle_manuals(s3: boto3.client) -> int:
    """
    Uploads all PDFs from data/raw_manuals/ into:
      s3://<bucket>/incoming/manuals/<filename>

    These are consumed by Snowflake's CORTEX.PARSE_DOCUMENT via external stage.
    """
    print("\nUploading vehicle manuals (PDFs)...")
    count = 0
    if not os.path.isdir(MANUALS_DIR):
        print(f"  Manuals directory not found: {MANUALS_DIR}")
        print("  Run: python data/generate_test_data.py")
        return 0

    for filename in sorted(os.listdir(MANUALS_DIR)):
        if not filename.endswith(".pdf"):
            continue
        local_path = os.path.join(MANUALS_DIR, filename)
        s3_key = f"incoming/manuals/{filename}"
        if upload_file(s3, local_path, s3_key, content_type="application/pdf"):
            count += 1

    return count


def upload_telemetry_events(s3: boto3.client) -> int:
    """
    Uploads all JSON telemetry files with Hive-style partitioning:
      s3://<bucket>/incoming/telemetry/source=<CLOUD>/date=<DATE>/<file>.json

    This partitioning lets Snowflake external tables query specific dates
    and sources efficiently without full-scan.
    """
    print("\nUploading telemetry events (JSON)...")
    count = 0
    if not os.path.isdir(TELEMETRY_DIR):
        print(f"  Telemetry directory not found: {TELEMETRY_DIR}")
        return 0

    for filename in sorted(os.listdir(TELEMETRY_DIR)):
        if not filename.endswith(".json"):
            continue

        local_path = os.path.join(TELEMETRY_DIR, filename)

        # Infer cloud source from filename for Hive partition
        if filename.startswith("aws_"):
            source = "AWS_S3"
        elif filename.startswith("azure_"):
            source = "AZURE_BLOB"
        else:
            source = "UNKNOWN"

        s3_key = f"incoming/telemetry/source={source}/date={TODAY}/{filename}"
        if upload_file(s3, local_path, s3_key, content_type="application/json"):
            count += 1

    return count


def print_s3_inventory(s3: boto3.client) -> None:
    """Prints a summary of all uploaded files."""
    print(f"\nS3 Bucket Inventory: s3://{S3_BUCKET}/incoming/")
    print("-" * 65)
    try:
        paginator = s3.get_paginator("list_objects_v2")
        total_size = 0
        total_files = 0
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix="incoming/"):
            for obj in page.get("Contents", []):
                size_kb = obj["Size"] // 1024
                print(f"  {obj['Key']:<55} {size_kb:>4} KB")
                total_size += obj["Size"]
                total_files += 1
        print("-" * 65)
        print(f"  Total: {total_files} files | {total_size // 1024} KB")
    except ClientError as e:
        print(f"  Could not list inventory: {e}")


if __name__ == "__main__":
    s3 = get_s3_client()
    ensure_bucket_exists(s3)

    pdf_count  = upload_vehicle_manuals(s3)
    json_count = upload_telemetry_events(s3)

    print_s3_inventory(s3)

    print(f"""
Pipeline Step 1 of 3 Complete
  PDFs uploaded  : {pdf_count}  -> s3://{S3_BUCKET}/incoming/manuals/
  JSON uploaded  : {json_count} -> s3://{S3_BUCKET}/incoming/telemetry/

Next steps:
  1. Snowflake: ALTER STAGE S3_MANUALS_STAGE REFRESH;
  2. Run: dbt run --select brz_telematics_raw slv_telematics slv_fault_analysis
  3. Run: dbt run --select gld_dealership_errors gld_ai_audit_report
""")
