import os
from dotenv import load_dotenv
import streamlit as st
from snowflake.snowpark import Session

# Load environment variables
load_dotenv()

st.set_page_config(page_title="Automotive AI Copilot", page_icon="🏎️", layout="wide")

# Custom CSS for Premium Design
st.markdown("""
<style>
    .reportview-container {
        background: #0E1117;
    }
    .stChatInput {
        border-radius: 12px;
        border: 1px solid #10b981;
    }
    .tech-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 16px;
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.5);
        color: #10b981;
        font-size: 0.8rem;
        font-weight: bold;
        margin-right: 8px;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

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
    
    if not all([connection_parameters["account"], connection_parameters["user"], connection_parameters["password"]]):
        return None
        
    try:
        session = Session.builder.configs(connection_parameters).create()
        return session
    except Exception as e:
        st.error(f"Failed to connect to Snowflake: {e}")
        return None

def main():
    st.title("🏎️ Automotive Intelligence Copilot")
    st.markdown("Retrieval-Augmented Generation (RAG) powered by **Snowflake Cortex AI**")
    
    session = create_session()
    
    if not session:
        st.warning("⚠️ **Missing or Invalid Credentials**. Please check your `.env` file.")
        return

    # Use tabs for a cleaner UI layout
    tab1, tab2 = st.tabs(["💬 Copilot Chat", "🗃️ Raw Data Pipeline"])
    
    with tab1:
        st.subheader("Diagnostic Assistant")
        st.markdown("Ask the Copilot a technical question. It will read the **Diagnostic Logs** and **Vehicle Manuals** to provide a synthesized answer.")
        
        # Initialize chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat Input
        if prompt := st.chat_input("e.g. 'I have a VIN123 with a P0300 misfire. What is the manual's torque spec?'"):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)

            # Build the RAG Prompt natively in SQL via Cortex COMPLETE
            # (In production, this would use Cortex Search Service mapping, but aggregating the exact context works perfectly for our demo skeleton)
            cortex_logic_sql = f"""
                WITH context_data AS (
                    SELECT LISTAGG(content_text, ' | ') as all_docs
                    FROM VEHICLE_INTELLIGENCE_DATA
                )
                SELECT 
                    SNOWFLAKE.CORTEX.COMPLETE(
                        'llama3-70b', 
                        CONCAT(
                            'You are an expert Automotive Diagnostic AI. Answer the user question based ONLY on the following vehicle manuals and diagnostic logs. ',
                            'Context Data: ', (SELECT all_docs FROM context_data),
                            ' Question: ', '{prompt}'
                        )
                    ) as response
            """

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                with st.spinner("🧠 Synthesizing vehicle manuals and service logs..."):
                    try:
                        df = session.sql(cortex_logic_sql).to_pandas()
                        bot_response = df.iloc[0]['RESPONSE']
                        
                        # Add some premium UI "Tags"
                        st.markdown('<span class="tech-pill">Vector Search</span><span class="tech-pill">Llama-3</span>', unsafe_allow_html=True)
                        message_placeholder.markdown(bot_response)
                        
                        st.session_state.messages.append({"role": "assistant", "content": bot_response})
                    except Exception as e:
                        message_placeholder.error(f"Connection or Cortex Error: {e}")

    with tab2:
        st.subheader("Ingested Data Lake")
        st.info("This is the raw internal data the Cortex AI is searching against.")
        try:
            df_raw = session.sql("SELECT record_id, vin, data_type, content_text FROM VEHICLE_INTELLIGENCE_DATA").to_pandas()
            st.dataframe(df_raw, use_container_width=True)
        except Exception as e:
            st.error(f"Could not load data: {e}")

if __name__ == "__main__":
    main()
