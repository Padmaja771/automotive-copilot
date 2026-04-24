from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
from airflow.operators.python import PythonOperator
from airflow.sensors.s3_key_sensor import S3KeySensor

# ==========================================================
# Automotive Intelligence Copilot — Main Pipeline Orchestrator
# ==========================================================
# This DAG demonstrates:
# 1. S3 Event Monitoring (Sensor)
# 2. Cross-system orchestration (AWS -> Snowflake)
# 3. Modular task design (Senior-level pattern)
# ==========================================================

default_args = {
    'owner': 'data_engineer',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'automotive_copilot_pipeline',
    default_args=default_args,
    description='Orchestrates PDF ingestion, Cortex parsing, and dbt transformations',
    schedule_interval=timedelta(hours=1),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['automotive', 'ai', 'cortex'],
) as dag:

    # 1. Wait for a new manual to arrive in S3
    # Demonstrates: Event-driven cloud sensors
    wait_for_s3_manual = S3KeySensor(
        task_id='wait_for_s3_manual',
        bucket_name='automotive-copilot-vehicle-docs-dev', # Terraform output
        bucket_key='incoming/*.pdf',
        wildcard_match=True,
        aws_conn_id='aws_default',
        timeout=18 * 60 * 60,
        poke_interval=60,
    )

    # 2. Trigger the Snowflake Cortex Parsing Procedure
    # Demonstrates: Snowflake Operator + Stored Proc calls
    trigger_cortex_parsing = SnowflakeOperator(
        task_id='trigger_cortex_parsing',
        snowflake_conn_id='snowflake_default',
        sql="CALL PROCESS_PENDING_PDFS();",
        warehouse='AI_PROJECT_WH',
        database='AI_PROJECT_DB',
        schema='STAGING',
    )

    # 3. Run dbt Transformations (Build Data Vault & Marts)
    # Note: In production, we use the BashOperator or Cosmos to run dbt
    run_dbt_transformations = SnowflakeOperator(
        task_id='run_dbt_transformations',
        snowflake_conn_id='snowflake_default',
        sql="""
            -- This is a placeholder for where Airflow would trigger dbt
            -- In our project, dbt will handle the Hub/Satellite logic
            SELECT 1; 
        """,
    )

    # 4. Data Quality Check (Observability)
    # JD Requirement: "Integration with monitoring and observability"
    verify_ingestion_quality = SnowflakeOperator(
        task_id='verify_ingestion_quality',
        snowflake_conn_id='snowflake_default',
        sql="""
            SELECT COUNT(*) 
            FROM VEHICLE_MANUALS_PARSED 
            WHERE extracted_at > DATEADD(hour, -1, CURRENT_TIMESTAMP());
        """,
    )

    # Define Dependencies
    wait_for_s3_manual >> trigger_cortex_parsing >> run_dbt_transformations >> verify_ingestion_quality
