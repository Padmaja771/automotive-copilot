"""
Lambda Handler: PDF Ingestion Processor
========================================
Triggered by S3 ObjectCreated events on the vehicle-docs bucket.

Security:
  - Snowflake credentials fetched from AWS Secrets Manager (never hardcoded)
  - Input validation on file type and size
  - Structured JSON logging for CloudWatch + observability

Flow:
  1. S3 event arrives with the uploaded PDF key
  2. Lambda validates the file (type, size)
  3. Lambda connects to Snowflake via Secrets Manager credentials
  4. Lambda registers the file in a PENDING_INGESTION table
  5. A Snowflake TASK (server-side) picks up PENDING rows
     and runs CORTEX.PARSE_DOCUMENT asynchronously
"""

import json
import logging
import os
import urllib.parse
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Constants
MAX_FILE_SIZE_MB = 50
ALLOWED_EXTENSIONS = {".pdf"}


def get_snowflake_credentials():
    """Fetch Snowflake credentials from AWS Secrets Manager."""
    secret_arn = os.environ["SNOWFLAKE_SECRET_ARN"]
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_arn)
    return json.loads(response["SecretString"])


def validate_s3_event(record: dict) -> dict:
    """Validate and extract metadata from an S3 event record.
    
    Returns:
        dict with bucket, key, size_mb, extension
    
    Raises:
        ValueError if the file fails validation
    """
    bucket = record["s3"]["bucket"]["name"]
    key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
    size_bytes = record["s3"]["object"].get("size", 0)
    size_mb = size_bytes / (1024 * 1024)

    # File extension check
    extension = os.path.splitext(key)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Rejected file '{key}': unsupported extension '{extension}'")

    # File size check
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(f"Rejected file '{key}': {size_mb:.1f}MB exceeds {MAX_FILE_SIZE_MB}MB limit")

    return {
        "bucket": bucket,
        "key": key,
        "size_mb": round(size_mb, 2),
        "extension": extension,
        "filename": os.path.basename(key),
    }


def register_in_snowflake(file_meta: dict, credentials: dict):
    """Register the uploaded file in Snowflake's PENDING_INGESTION table.
    
    This is a lightweight INSERT. The heavy Cortex PARSE_DOCUMENT work
    is handled by a Snowflake TASK on a schedule (server-side).
    """
    import snowflake.connector

    conn = snowflake.connector.connect(
        account=credentials["account"],
        user=credentials["user"],
        password=credentials["password"],
        role=credentials["role"],
        warehouse=credentials["warehouse"],
        database=credentials["database"],
        schema=credentials["schema"],
    )

    try:
        cursor = conn.cursor()

        # Extract VIN reference from filename convention: VIN123_engine_manual.pdf
        vin_reference = file_meta["filename"].split("_")[0] if "_" in file_meta["filename"] else "UNKNOWN"

        cursor.execute(
            """
            INSERT INTO PENDING_INGESTION (s3_bucket, s3_key, filename, vin_reference, file_size_mb, status)
            VALUES (%s, %s, %s, %s, %s, 'PENDING')
            """,
            (
                file_meta["bucket"],
                file_meta["key"],
                file_meta["filename"],
                vin_reference,
                file_meta["size_mb"],
            ),
        )

        logger.info(f"Registered '{file_meta['filename']}' in PENDING_INGESTION (VIN: {vin_reference})")
    finally:
        conn.close()


def lambda_handler(event, context):
    """Main Lambda entry point. Processes S3 event records."""
    logger.info(json.dumps({"message": "Lambda invoked", "event": event}))

    credentials = None
    processed = 0
    errors = 0

    for record in event.get("Records", []):
        try:
            # 1. Validate the uploaded file
            file_meta = validate_s3_event(record)
            logger.info(json.dumps({
                "message": "File validated",
                "file": file_meta["filename"],
                "size_mb": file_meta["size_mb"],
            }))

            # 2. Lazy-load Snowflake credentials (once per invocation)
            if credentials is None:
                credentials = get_snowflake_credentials()
                logger.info("Snowflake credentials loaded from Secrets Manager")

            # 3. Register the file for processing
            register_in_snowflake(file_meta, credentials)
            processed += 1

        except ValueError as ve:
            logger.warning(json.dumps({"message": "Validation failed", "error": str(ve)}))
            errors += 1
        except Exception as e:
            logger.error(json.dumps({"message": "Processing failed", "error": str(e)}))
            errors += 1

    result = {
        "statusCode": 200,
        "body": json.dumps({
            "processed": processed,
            "errors": errors,
            "total_records": len(event.get("Records", [])),
        }),
    }

    logger.info(json.dumps({"message": "Lambda complete", "result": result["body"]}))
    return result
