import os
from dotenv import load_dotenv
import streamlit as st
from snowflake.snowpark import Session

# Load environment variables
load_dotenv()

st.set_page_config(page_title="Automotive AI Copilot", page_icon="🚗", layout="wide")

@st.cache_resource
def create_session():
    """Create a Snowpark session from environment variables."""
    connection_parameters = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "role": os.getenv("SNOWFLAKE_ROLE", "CORTEX_DEV_ROLE"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "AI_PROJECT_WH"),
        "database": os.getenv("SNOWFLAKE_DATABASE", "AI_PROJECT_DB"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA", "STAGING"),
    }
    
    # Check if necessary credentials are provided
    if not all([connection_parameters["account"], connection_parameters["user"], connection_parameters["password"]]):
        return None
        
    try:
        session = Session.builder.configs(connection_parameters).create()
        return session
    except Exception as e:
        st.error(f"Failed to connect to Snowflake: {e}")
        return None

def main():
    st.title("🚗 Automotive Intelligence Copilot")
    st.markdown("Powered by **Snowflake Cortex AI**")
    
    session = create_session()
    
    if not session:
        st.warning("⚠️ **Missing or Invalid Credentials**")
        st.info("Please create a `.env` file based on `.env.example` in the root of your project directory with your Snowflake connection details.")
        return
        
    st.success("✅ Connected to Snowflake successfully!")
    
    st.subheader("Vehicle Diagnostic & Manual Intelligence")
    
    # Run the Cortex AI query right from Streamlit
    query = """
        SELECT 
            vin,
            data_type,
            content_text,
            SNOWFLAKE.CORTEX.SUMMARIZE(content_text) as ai_summary,
            SNOWFLAKE.CORTEX.EXTRACT_ANSWER(content_text, 'What is the specific fix or technical spec mentioned?') as technical_spec
        FROM VEHICLE_INTELLIGENCE_DATA
    """
    
    with st.spinner("Cortex AI is analyzing records..."):
        try:
            df = session.sql(query).to_pandas()
            st.dataframe(df, use_container_width=True)
            
            # Simple metrics
            st.metric("Total Records Processed", len(df))
        except Exception as e:
            st.error(f"Query Failed: {e}")

if __name__ == "__main__":
    main()
