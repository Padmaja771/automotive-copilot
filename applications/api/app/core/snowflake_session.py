import os
from snowflake.snowpark import Session
from dotenv import load_dotenv

load_dotenv()

def get_snowpark_session():
    """Returns a production Snowflake Snowpark session using ENV credentials."""
    connection_parameters = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "role": os.getenv("SNOWFLAKE_ROLE", "CORTEX_DEV_ROLE"),  # NEVER default to ACCOUNTADMIN
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE", "AI_PROJECT_DB"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA", "STAGING")
    }
    
    # Check if we have the minimum required keys
    if not connection_parameters["account"] or not connection_parameters["user"]:
        # Fallback for dev environment if no credentials provided yet
        return None
        
    try:
        return Session.builder.configs(connection_parameters).create()
    except Exception as e:
        print(f"Snowflake Session Error: {e}")
        return None
