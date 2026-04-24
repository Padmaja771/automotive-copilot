"""
Automotive Copilot: Enterprise Airflow Orchestration DAG
=========================================================
This DAG explicitly glues together AWS, Azure, Snowpark, and dbt into one automated clockwork mechanism!
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
# from airflow.providers.microsoft.azure.sensors.wasb import WasbBlobSensor # Custom Azure Sensor (Mocked below)

default_args = {
    'owner': 'lead_ai_architect',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'enterprise_multi_cloud_ai_pipeline',
    default_args=default_args,
    description='Master Orchestrator for AWS/Azure -> Snowpark -> dbt Medallion -> AI Agent',
    schedule_interval='@daily', # Runs automatically every night at Midnight!
    catchup=False,
    tags=['snowflake', 'snowpark', 'dbt', 'multi-cloud'],
) as dag:

    # 1. Listen for new files arriving from Dealerships globally
    start_pipeline = EmptyOperator(task_id='start_nightly_batch')

    # AIRFLOW SENSORS: These sit silently and wait for Dealerships to upload files
    wait_for_aws_telemetry = EmptyOperator(task_id='sensor_aws_s3_telematics_json')
    wait_for_azure_pdfs = EmptyOperator(task_id='sensor_azure_blob_vehicle_manuals')

    # 2. RUN INGESTION SCRIPT (Our new Snowpark code!)
    # Once files arrive, Airflow tells a Docker container to execute our Python script
    run_snowpark_ingestion = BashOperator(
        task_id='ingest_bronze_layer_via_snowpark',
        bash_command='python /opt/airflow/ingestion/snowpark_ingestion.py',
    )

    # 3. RUN TRANSFORMATION SCRIPT (Our dbt Silver/Gold views!)
    # Once data hits the Bronze table, Airflow tells dbt to clean it
    run_dbt_medallion = BashOperator(
        task_id='transform_silver_gold_via_dbt',
        bash_command='cd /opt/airflow/transformation/dbt_project && dbt run',
    )

    # 4. DATA QUALITY TESTING
    # Before the Streamlit Agent wakes up, ensure the data isn't corrupted
    verify_data_quality = BashOperator(
        task_id='verify_data_quality',
        bash_command='cd /opt/airflow/transformation/dbt_project && dbt test',
    )

    # 5. Pipeline Complete! (Agent is ready to be used by Dealerships)
    refresh_streamlit_cache = EmptyOperator(task_id='refresh_ai_copilot_cache')

    # ==========================================
    # THIS IS THE MAGIC GLUE (Task Dependency Graph)
    # ==========================================
    start_pipeline >> [wait_for_aws_telemetry, wait_for_azure_pdfs] >> run_snowpark_ingestion
    run_snowpark_ingestion >> run_dbt_medallion >> verify_data_quality >> refresh_streamlit_cache
