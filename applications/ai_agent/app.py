import os
import json
from dotenv import load_dotenv
import streamlit as st
from snowflake.snowpark import Session

# Load environment variables
load_dotenv()

st.set_page_config(page_title="Automotive AI Copilot (Agent Edition)", page_icon="🤖", layout="wide")

# Custom CSS for Premium Design
st.markdown("""
<style>
    .reportview-container { background: #0E1117; }
    .stChatInput { border-radius: 12px; border: 1px solid #10b981; }
    .tech-pill {
        display: inline-block; padding: 4px 12px; border-radius: 16px;
        background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.5);
        color: #10b981; font-size: 0.8rem; font-weight: bold; margin-right: 8px; margin-bottom: 8px;
    }
    .tool-pill { background: rgba(59, 130, 246, 0.15); color: #3b82f6; border-color: rgba(59, 130, 246, 0.5); }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def create_session():
    """Create a Snowpark session from environment variables."""
    conn_params = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "role": os.getenv("SNOWFLAKE_ROLE", "CORTEX_DEV_ROLE"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "AI_PROJECT_WH"),
        "database": os.getenv("SNOWFLAKE_DATABASE", "AI_PROJECT_DB"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA", "STAGING"),
    }
    try:
        return Session.builder.configs(conn_params).create()
    except Exception as e:
        st.error(f"Failed to connect to Snowflake: {e}")
        return None

# ==========================================
# AGENT TOOLS (Fulfills the Job Requirement)
# ==========================================
def tool_query_parsed_manuals(session, vin_reference):
    """Tool: Queries the dbt-generated semantic layer for vehicle manuals."""
    try:
        # Note: We are hitting our dbt table!
        query = f"SELECT chunk_text FROM DBT_MODELS.parsed_vehicle_manuals WHERE vin_reference = '{vin_reference}' LIMIT 3;"
        df = session.sql(query).to_pandas()
        return " | ".join(df['CHUNK_TEXT'].tolist()) if not df.empty else "No manual data found for this VIN."
    except:
        return "Manual database currently syncing."

def tool_query_diagnostic_logs(session, vin_reference):
    """Tool: Queries rapid ingest logs from Snowflake."""
    try:
        query = f"SELECT content_text FROM STAGING.VEHICLE_INTELLIGENCE_DATA WHERE vin = '{vin_reference}' AND data_type = 'DIAGNOSTIC_LOG' LIMIT 1;"
        df = session.sql(query).to_pandas()
        return df['CONTENT_TEXT'].iloc[0] if not df.empty else "No diagnostic logs found."
    except:
        return "Diagnostic system unavailable."

# ==========================================
# AGENT ORCHESTRATOR
# ==========================================
def run_agentic_workflow(session, prompt: str):
    """
    Simulates LLM Tool Calling orchestration.
    1. The Agent decides which tools to call
    2. Gathers the context
    3. Synthesizes a response using Snowflake Cortex
    """
    st.markdown('<span class="tech-pill tool-pill">🚨 Guardrail Check</span>', unsafe_allow_html=True)
    
    # 0. Security Guardrail (Block non-automotive prompts to save Snowflake tokens)
    clean_prompt = prompt.replace("'", "")
    guardrail_sql = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3-70b', 'Answer YES or NO only. Is this sequence of words asking about cars, vehicles, diagnostics, or automotive things? Question: {clean_prompt}')"
    is_valid = session.sql(guardrail_sql).collect()[0][0].strip().upper()
    
    if "YES" not in is_valid:
        return "I am an Automotive AI. I cannot answer queries unrelated to vehicles and diagnostics!"

    st.markdown('<span class="tech-pill tool-pill">⚙️ Agent Routing Request</span>', unsafe_allow_html=True)
    
    # 1. Intent Extraction (Agent decides which tools to use)
    # Using Cortex to figure out the VIN
    vin_extract_sql = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3-70b', 'Extract just the VIN number from this prompt, nothing else. If none, say NONE: {prompt}') as vin_res"
    vin_reference = session.sql(vin_extract_sql).collect()[0][0].strip()

    context = ""
    # 2. Tool Execution
    if vin_reference and vin_reference != "NONE":
        st.markdown(f'<span class="tech-pill tool-pill">🔧 Tool Call: `query_parsed_manuals(vin="{vin_reference}")`</span>', unsafe_allow_html=True)
        manual_context = tool_query_parsed_manuals(session, vin_reference)
        
        st.markdown(f'<span class="tech-pill tool-pill">🔧 Tool Call: `query_diagnostic_logs(vin="{vin_reference}")`</span>', unsafe_allow_html=True)
        log_context = tool_query_diagnostic_logs(session, vin_reference)
        
        context = f"Manual Reference: {manual_context}\nDiagnostic Logs: {log_context}"
    else:
        st.markdown('<span class="tech-pill tool-pill">🔧 Tool Call: `general_knowledge_fallback()`</span>', unsafe_allow_html=True)
        context = "No specific vehicle found. Be generally helpful."

    # 3. Final Synthesis (RAG)
    final_prompt = f"""
        You are an expert Automotive Diagnostic AI Agent.
        Answer the user's question securely using ONLY the Tool Context provided below.
        If the tools returned nothing, state that you don't have the data.
        
        Tool Context:
        {context}
        
        User Question: {prompt}
    """
    
    synthesis_sql = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3-70b', '{final_prompt.replace(chr(39), chr(39)+chr(39))}') as response"
    return session.sql(synthesis_sql).collect()[0][0]

def main():
    st.title("🤖 Automotive Intelligence Copilot (Agent Edition)")
    st.markdown("Fully Autonomous Agent orchestration using **Snowflake Cortex AI** and **dbt semantic models**.")
    
    session = create_session()
    if not session:
        st.warning("⚠️ **Missing or Invalid Credentials**.")
        return

    tab1, tab2 = st.tabs(["💬 Agent Chat", "🗃️ dbt Semantic Layer (Marts)"])
    
    with tab1:
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("e.g. 'What is the standard procedure for replacing a transmission on VIN123?'"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                with st.spinner("🤖 Agent is Orchestrating Tools..."):
                    try:
                        bot_response = run_agentic_workflow(session, prompt)
                        st.markdown('<span class="tech-pill">Snowflake Cortex</span><span class="tech-pill">LLaMA 3</span>', unsafe_allow_html=True)
                        message_placeholder.markdown(bot_response)
                        st.session_state.messages.append({"role": "assistant", "content": bot_response})
                    except Exception as e:
                        message_placeholder.error(f"Agent Orchestration Error: {e}")

    with tab2:
        st.subheader("dbt Transformed Pipeline `parsed_vehicle_manuals`")
        st.info("The Agent dynamically uses tools to read from this semantic layer we built in Day 2.")
        try:
            df_raw = session.sql("SELECT source_file, vin_reference, chunk_index, extracted_at FROM DBT_MODELS.parsed_vehicle_manuals").to_pandas()
            st.dataframe(df_raw, use_container_width=True)
        except Exception:
            st.warning("dbt modeling not fully deployed yet. Run `dbt run`!")

if __name__ == "__main__":
    main()
