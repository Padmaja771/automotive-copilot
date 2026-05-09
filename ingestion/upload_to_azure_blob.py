"""
Azure Blob Storage Upload — Telemetry JSON + Vehicle Manual PDFs
=================================================================
Mirrors the AWS S3 upload but targets Azure Blob Storage.
Simulates files arriving from Azure-connected dealerships.

Container layout:
  vehicle-docs (container)
  ├── manuals/                          <- PDFs for Cortex PARSE_DOCUMENT
  └── telemetry/
      ├── source=AZURE_BLOB/date=<DATE>/azure_gen2_bmw_honda.json
      └── source=AWS_S3/date=<DATE>/aws_gen1_ford_toyota.json

Run:  python ingestion/upload_to_azure_blob.py
Requires: pip install azure-storage-blob
          AZURE_STORAGE_CONNECTION_STRING in .env
          OR AZURE_STORAGE_ACCOUNT_NAME + AZURE_STORAGE_ACCOUNT_KEY
"""

import os
import sys
from datetime import datetime, UTC
from dotenv import load_dotenv

load_dotenv()

LOCAL_ROOT    = os.path.join(os.path.dirname(__file__), "..", "data")
TELEMETRY_DIR = os.path.join(LOCAL_ROOT, "raw_cloud_events")
MANUALS_DIR   = os.path.join(LOCAL_ROOT, "raw_manuals")
CONTAINER     = os.getenv("AZURE_CONTAINER_NAME", "vehicle-docs")
TODAY         = datetime.now(UTC).strftime("%Y-%m-%d")


def get_blob_service_client():
    """Returns an authenticated Azure BlobServiceClient."""
    try:
        from azure.storage.blob import BlobServiceClient
        from azure.core.exceptions import AzureError
    except ImportError:
        print("azure-storage-blob not installed. Installing...")
        os.system(f"{sys.executable} -m pip install azure-storage-blob -q")
        from azure.storage.blob import BlobServiceClient
        from azure.core.exceptions import AzureError

    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    account  = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    key      = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")

    if conn_str:
        client = BlobServiceClient.from_connection_string(conn_str)
        print("Connected to Azure Blob Storage (connection string)")
    elif account and key:
        url = f"https://{account}.blob.core.windows.net"
        from azure.storage.blob import StorageSharedKeyCredential
        cred = StorageSharedKeyCredential(account, key)
        client = BlobServiceClient(account_url=url, credential=cred)
        print(f"Connected to Azure Blob Storage (account: {account})")
    else:
        print("ERROR: Azure credentials not found.")
        print("  Set AZURE_STORAGE_CONNECTION_STRING in your .env file")
        print("  or AZURE_STORAGE_ACCOUNT_NAME + AZURE_STORAGE_ACCOUNT_KEY")
        sys.exit(1)

    return client


def ensure_container_exists(client) -> None:
    """Creates the Blob container if it doesn't exist."""
    container_client = client.get_container_client(CONTAINER)
    try:
        container_client.get_container_properties()
        print(f"Container exists: {CONTAINER}")
    except Exception:
        print(f"Creating container: {CONTAINER}")
        container_client.create_container()


def upload_blob(client, local_path: str, blob_name: str,
                content_type: str = "application/octet-stream") -> bool:
    """Uploads a single file to Azure Blob Storage."""
    try:
        from azure.storage.blob import ContentSettings
        size = os.path.getsize(local_path)
        blob_client = client.get_blob_client(container=CONTAINER, blob=blob_name)

        with open(local_path, "rb") as data:
            blob_client.upload_blob(
                data,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type),
                metadata={
                    "uploaded_by":    "automotive-copilot-pipeline",
                    "upload_date":    TODAY,
                    "pipeline_stage": "raw-ingestion",
                }
            )
        print(f"  UPLOADED  {CONTAINER}/{blob_name}  ({size // 1024} KB)")
        return True
    except Exception as e:
        print(f"  FAILED    {os.path.basename(local_path)}: {e}")
        return False


def upload_vehicle_manuals(client) -> int:
    """Uploads PDFs to manuals/ prefix in Azure Blob."""
    print("\nUploading vehicle manuals (PDFs) to Azure...")
    count = 0
    for filename in sorted(os.listdir(MANUALS_DIR)):
        if not filename.endswith(".pdf"):
            continue
        local_path = os.path.join(MANUALS_DIR, filename)
        blob_name = f"manuals/{filename}"
        if upload_blob(client, local_path, blob_name, "application/pdf"):
            count += 1
    return count


def upload_telemetry_events(client) -> int:
    """Uploads JSON events with Hive-style partitioning to Azure Blob."""
    print("\nUploading telemetry events (JSON) to Azure...")
    count = 0
    for filename in sorted(os.listdir(TELEMETRY_DIR)):
        if not filename.endswith(".json"):
            continue
        local_path = os.path.join(TELEMETRY_DIR, filename)
        source = "AZURE_BLOB" if filename.startswith("azure_") else "AWS_S3"
        blob_name = f"telemetry/source={source}/date={TODAY}/{filename}"
        if upload_blob(client, local_path, blob_name, "application/json"):
            count += 1
    return count


def print_blob_inventory(client) -> None:
    """Prints a summary of all blobs in the container."""
    print(f"\nAzure Blob Inventory: {CONTAINER}/")
    print("-" * 65)
    container_client = client.get_container_client(CONTAINER)
    total_size = 0
    total_files = 0
    for blob in container_client.list_blobs():
        size_kb = blob.size // 1024
        print(f"  {blob.name:<55} {size_kb:>4} KB")
        total_size += blob.size
        total_files += 1
    print("-" * 65)
    print(f"  Total: {total_files} files | {total_size // 1024} KB")


if __name__ == "__main__":
    client = get_blob_service_client()
    ensure_container_exists(client)

    pdf_count  = upload_vehicle_manuals(client)
    json_count = upload_telemetry_events(client)

    print_blob_inventory(client)

    print(f"""
Pipeline Step 1 of 3 Complete (Azure)
  PDFs uploaded  : {pdf_count}  -> {CONTAINER}/manuals/
  JSON uploaded  : {json_count} -> {CONTAINER}/telemetry/

Next steps:
  1. Snowflake: ALTER STAGE AZURE_MANUALS_STAGE REFRESH;
  2. Run: dbt run --select brz_telematics_raw slv_telematics
  3. Run: dbt run --select gld_dealership_errors
""")
