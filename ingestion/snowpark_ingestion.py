import os
import json
import pandas as pd
from dotenv import load_dotenv
from snowflake.snowpark import Session

# Load standard credentials
load_dotenv()

def create_snowpark_session():
    conn_params = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "role": os.getenv("SNOWFLAKE_ROLE", "CORTEX_DEV_ROLE"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "AI_PROJECT_WH"),
        "database": os.getenv("SNOWFLAKE_DATABASE", "AI_PROJECT_DB"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA", "STAGING"),
    }
    return Session.builder.configs(conn_params).create()

def ingest_telematics_with_snowpark(session):
    print("🚀 Connecting to Snowflake via Snowpark...")
    
    # Simulate real-time pipelines dropping files into our Cloud Storage!
    data_folder = "data/raw_cloud_events/"
    all_telemetry = []

    print(f"📡 Scanning for new JSON pushes from AWS mapping & Azure mappings...")
    for filename in os.listdir(data_folder):
        if filename.endswith(".json"):
            filepath = os.path.join(data_folder, filename)
            print(f"   => New real-time event detected: {filename}")
            
            with open(filepath, 'r') as f:
                # 1. READ: Extract raw unstructured data
                raw_data = json.load(f)
                all_telemetry.extend(raw_data)

    if not all_telemetry:
        print("No new events to process.")
        return

    # 2. TRANSFORM: Convert "ERROR" to -999 natively in Python
    for record in all_telemetry:
        if record.get("engine_temp_c") == "ERROR":
            record["engine_temp_c"] = -999.0
        else:
            record["engine_temp_c"] = float(record["engine_temp_c"])

    print("\n✅ Transformed Payload (Ready for Snowflake):")
    for r in all_telemetry:
        print(f"VIN: {r['vin']} | Temp: {r['engine_temp_c']} | Error: {r['error_code']}")

    # 3. LOAD: Physically push into Snowflake BRONZE using Snowpark
    table_name = "STAGING.BRONZE_TELEMATICS"
    
    # Convert dicts to a list of tuples for Snowpark native ingestion
    data_tuples = [(r["vin"], r["engine_temp_c"], r["error_code"], r["cloud_source"]) for r in all_telemetry]
    
    # Upload instantly using Snowflake's native DataFrames!
    snowpark_df = session.create_dataframe(data_tuples, schema=["VIN", "ENGINE_TEMP_C", "ERROR_CODE", "CLOUD_SOURCE"])
    
    # Fix: Use 'overwrite' because we just added the 4th column (CLOUD_SOURCE) to a 3-column table!
    snowpark_df.write.mode("overwrite").save_as_table(table_name)
    
    print(f"\n📦 Successfully wrote {len(data_tuples)} real-time records into {table_name}")

if __name__ == "__main__":
    session = create_snowpark_session()
    if session:
        ingest_telematics_with_snowpark(session)
    else:
        print("Failed to initialize Snowpark session.")
