# =========================================================================
# Automotive Intelligence Copilot — Streamlit in Snowflake Dashboard
# =========================================================================
# Deploy this file directly inside Snowflake:
#   Snowsight > Streamlit > + Create > Paste this file
#
# Required: ANALYST_ROLE or CORTEX_DEV_ROLE
# Databases: AI_PROJECT_DB (GOLD + SILVER schemas)
# =========================================================================

import streamlit as st
import pandas as pd
import json
import time
from snowflake.snowpark.context import get_active_session

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Automotive Intelligence Copilot",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0d1117; }
    [data-testid="stSidebar"]          { background-color: #161b22; }
    .metric-card {
        background: linear-gradient(135deg, #1c2333 0%, #21262d 100%);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .metric-value { font-size: 2.4rem; font-weight: 700; color: #58a6ff; }
    .metric-label { font-size: 0.85rem; color: #8b949e; margin-top: 4px; }
    .alert-high   { color: #f85149; }
    .alert-med    { color: #e3b341; }
    .alert-ok     { color: #3fb950; }
    h1, h2, h3    { color: #e6edf3; }
    p, label      { color: #c9d1d9; }
</style>
""", unsafe_allow_html=True)

# ── Snowflake Session ──────────────────────────────────────────────────────────
session = get_active_session()

# ── Cached Data Loaders ────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_dealership_summary():
    return session.sql("""
        SELECT
            VIN_REFERENCE,
            TOTAL_CRITICAL_ERRORS,
            MAX_ENGINE_TEMP_RECORDED,
            ARRAY_SIZE(DISTINCT_FAULT_CATEGORIES) AS num_fault_types,
            LAST_AGGREGATED_AT
        FROM AI_PROJECT_DB.GOLD.GLD_DEALERSHIP_ERRORS
        ORDER BY TOTAL_CRITICAL_ERRORS DESC
        LIMIT 50
    """).to_pandas()

@st.cache_data(ttl=300)
def load_fault_analysis():
    return session.sql("""
        SELECT
            VIN_MASKED,
            FAULT_CATEGORY,
            DRIVER_FRUSTRATION_SCORE,
            CONCISE_FAULT_SUMMARY,
            LOG_SUMMARY,
            DIAGNOSTIC_ERROR_CODE,
            ENGINE_TEMPERATURE_CELSIUS
        FROM AI_PROJECT_DB.SILVER.SLV_TELEMATICS
        WHERE FAULT_CATEGORY IS NOT NULL
        LIMIT 200
    """).to_pandas()

@st.cache_data(ttl=300)
def load_ai_audit_report():
    return session.sql("""
        SELECT
            VIN_REFERENCE,
            CORTEX_MODEL_USED,
            DIAGNOSIS_SUMMARY,
            CONFIDENCE_SCORE,
            FAITHFULNESS_SCORE,
            AUDIT_TIMESTAMP
        FROM AI_PROJECT_DB.GOLD.GLD_AI_AUDIT_REPORT
        ORDER BY AUDIT_TIMESTAMP DESC
        LIMIT 100
    """).to_pandas()

@st.cache_data(ttl=600)
def load_ml_predictions():
    return session.sql("""
        SELECT *
        FROM AI_PROJECT_DB.GOLD.GLD_DEALERSHIP_ERRORS
        WHERE TOTAL_CRITICAL_ERRORS > 5
        ORDER BY TOTAL_CRITICAL_ERRORS DESC
        LIMIT 30
    """).to_pandas()


# ── Sidebar Navigation ─────────────────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/fluency/96/car.png", width=60)
st.sidebar.title("Automotive Copilot")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["🏠 Fleet Overview", "🧠 AI Diagnostics", "📊 Fault Analysis", "✅ Model Quality"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("**🔒 Role:** `ANALYST_ROLE`")
st.sidebar.markdown("**❄️ Warehouse:** `API_QUERY_WH`")
st.sidebar.markdown("**🗄️ DB:** `AI_PROJECT_DB`")
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()


# =========================================================================
# PAGE 1: Fleet Overview
# =========================================================================
if page == "🏠 Fleet Overview":
    st.title("🚗 Automotive Intelligence Copilot")
    st.markdown("**Real-time fleet health powered by Snowflake Cortex AI + dbt Gold Layer**")
    st.markdown("---")

    with st.spinner("Loading fleet data..."):
        df_fleet = load_dealership_summary()
        df_faults = load_fault_analysis()

    # ── KPI Row ─────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_vehicles = len(df_fleet)
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{total_vehicles}</div>
            <div class="metric-label">Total Vehicles Monitored</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        critical = len(df_fleet[df_fleet['TOTAL_CRITICAL_ERRORS'] > 10])
        color = "alert-high" if critical > 0 else "alert-ok"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value {color}">{critical}</div>
            <div class="metric-label">High-Risk Vehicles (>10 faults)</div>
        </div>""", unsafe_allow_html=True)

    with col3:
        avg_temp = round(df_fleet['MAX_ENGINE_TEMP_RECORDED'].mean(), 1) if not df_fleet.empty else 0
        temp_color = "alert-high" if avg_temp > 120 else "alert-ok"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value {temp_color}">{avg_temp}°C</div>
            <div class="metric-label">Avg Max Engine Temp</div>
        </div>""", unsafe_allow_html=True)

    with col4:
        frustrated = len(df_faults[df_faults['DRIVER_FRUSTRATION_SCORE'] < -0.5]) if not df_faults.empty else 0
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value alert-med">{frustrated}</div>
            <div class="metric-label">High-Frustration Reports</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Top 15 Critical Vehicles ─────────────────────────────────────────────
    st.subheader("🚨 Vehicles Requiring Immediate Attention")
    if not df_fleet.empty:
        display_df = df_fleet[['VIN_REFERENCE', 'TOTAL_CRITICAL_ERRORS',
                                'MAX_ENGINE_TEMP_RECORDED', 'NUM_FAULT_TYPES']].head(15)
        st.dataframe(
            display_df,
            use_container_width=True,
            column_config={
                "VIN_REFERENCE":         st.column_config.TextColumn("VIN"),
                "TOTAL_CRITICAL_ERRORS": st.column_config.ProgressColumn("Critical Faults", max_value=int(df_fleet['TOTAL_CRITICAL_ERRORS'].max())),
                "MAX_ENGINE_TEMP_RECORDED": st.column_config.NumberColumn("Max Engine Temp (°C)", format="%.1f °C"),
                "NUM_FAULT_TYPES":       st.column_config.NumberColumn("Distinct Fault Types"),
            }
        )
    else:
        st.info("No data available. Run `dbt run` to populate the Gold layer.")


# =========================================================================
# PAGE 2: AI Diagnostics (Live Cortex Query)
# =========================================================================
elif page == "🧠 AI Diagnostics":
    st.title("🧠 Live AI Diagnostic Engine")
    st.markdown("**Powered by `SNOWFLAKE.CORTEX.COMPLETE` — all inference runs inside Snowflake (zero data egress)**")
    st.markdown("---")

    with st.form("diagnostic_form"):
        col1, col2 = st.columns([2, 1])
        with col1:
            symptoms = st.text_area(
                "Describe Vehicle Symptoms",
                placeholder="e.g. Engine misfires on cold start, rough idle, P0300 code detected...",
                height=120
            )
        with col2:
            vin_input = st.text_input("VIN (optional)", placeholder="e.g. VIN_AWS_001")
            error_code = st.text_input("OBD-II Code (optional)", placeholder="e.g. P0300")
            model_choice = st.selectbox("Cortex Model", ["mistral-large2", "llama3.1-70b", "claude-3-5-sonnet"])

        submitted = st.form_submit_button("🔍 Run Diagnosis", use_container_width=True)

    if submitted and symptoms:
        with st.spinner("Running Cortex inference inside Snowflake..."):
            start = time.time()

            prompt = f"""You are an expert automotive diagnostic AI.
A mechanic reports the following vehicle symptoms: {symptoms}
{"VIN: " + vin_input if vin_input else ""}
{"OBD Code: " + error_code if error_code else ""}

Return a JSON object with these exact keys:
{{
  "primary_diagnosis": "...",
  "confidence_score": 0.0-1.0,
  "root_cause": "...",
  "supporting_evidence": ["...", "..."],
  "recommended_actions": ["...", "..."],
  "estimated_severity": "LOW|MEDIUM|HIGH|CRITICAL"
}}
Return ONLY the JSON, no other text."""

            result = session.sql(f"""
                SELECT SNOWFLAKE.CORTEX.COMPLETE('{model_choice}', '{prompt.replace("'", "''")}') AS DIAGNOSIS
            """).collect()

            elapsed = round(time.time() - start, 2)
            raw_response = result[0]['DIAGNOSIS'] if result else "{}"

        try:
            data = json.loads(raw_response)
            severity = data.get("estimated_severity", "UNKNOWN")
            sev_color = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(severity, "⚪")

            st.success(f"Diagnosis complete in **{elapsed}s** — Model: `{model_choice}`")
            st.markdown("---")

            col1, col2, col3 = st.columns(3)
            col1.metric("Confidence Score", f"{data.get('confidence_score', 0) * 100:.0f}%")
            col2.metric("Severity", f"{sev_color} {severity}")
            col3.metric("Inference Time", f"{elapsed}s")

            st.subheader("🎯 Primary Diagnosis")
            st.info(data.get("primary_diagnosis", "N/A"))

            st.subheader("🔬 Root Cause")
            st.warning(data.get("root_cause", "N/A"))

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📋 Recommended Actions")
                for i, action in enumerate(data.get("recommended_actions", []), 1):
                    st.markdown(f"**{i}.** {action}")

            with col2:
                st.subheader("📄 Supporting Evidence")
                for evidence in data.get("supporting_evidence", []):
                    st.markdown(f"• {evidence}")

        except (json.JSONDecodeError, KeyError):
            st.subheader("Raw Response")
            st.code(raw_response, language="json")

    elif submitted:
        st.warning("Please enter vehicle symptoms to run a diagnosis.")


# =========================================================================
# PAGE 3: Fault Analysis (Cortex-Enriched Silver Layer)
# =========================================================================
elif page == "📊 Fault Analysis":
    st.title("📊 AI-Enriched Fault Analysis")
    st.markdown("**Data from `SLV_TELEMATICS` — enriched by Cortex SUMMARIZE + COMPLETE classification**")
    st.markdown("---")

    with st.spinner("Loading fault data..."):
        df = load_fault_analysis()

    if df.empty:
        st.info("No data available. Run `dbt run` to populate the Silver layer.")
    else:
        # ── Filter Panel ──────────────────────────────────────────────────────
        col1, col2 = st.columns(2)
        with col1:
            categories = ["All"] + sorted(df['FAULT_CATEGORY'].dropna().unique().tolist())
            selected_cat = st.selectbox("Filter by Fault Category", categories)
        with col2:
            frustration_threshold = st.slider("Max Frustration Score", -1.0, 1.0, 1.0, 0.1)

        df_filtered = df.copy()
        if selected_cat != "All":
            df_filtered = df_filtered[df_filtered['FAULT_CATEGORY'] == selected_cat]
        df_filtered = df_filtered[df_filtered['DRIVER_FRUSTRATION_SCORE'] <= frustration_threshold]

        st.markdown(f"**Showing {len(df_filtered)} faults**")

        # ── Fault Category Distribution ───────────────────────────────────────
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Fault Categories")
            cat_counts = df['FAULT_CATEGORY'].value_counts().reset_index()
            cat_counts.columns = ['Category', 'Count']
            st.dataframe(cat_counts, use_container_width=True, hide_index=True)

        with col2:
            st.subheader("Frustration Score Distribution")
            st.bar_chart(
                df_filtered['DRIVER_FRUSTRATION_SCORE'].dropna(),
                use_container_width=True
            )

        # ── Fault Table ───────────────────────────────────────────────────────
        st.subheader("Fault Log — AI Enriched")
        display_cols = ['VIN_MASKED', 'FAULT_CATEGORY', 'DRIVER_FRUSTRATION_SCORE',
                        'DIAGNOSTIC_ERROR_CODE', 'CONCISE_FAULT_SUMMARY']
        available = [c for c in display_cols if c in df_filtered.columns]
        st.dataframe(
            df_filtered[available].head(50),
            use_container_width=True,
            column_config={
                "DRIVER_FRUSTRATION_SCORE": st.column_config.ProgressColumn(
                    "Frustration", min_value=-1.0, max_value=1.0
                ),
                "FAULT_CATEGORY": st.column_config.TextColumn("Category"),
                "CONCISE_FAULT_SUMMARY": st.column_config.TextColumn("AI Summary", width="large")
            }
        )


# =========================================================================
# PAGE 4: Model Quality (AI Audit Report)
# =========================================================================
elif page == "✅ Model Quality":
    st.title("✅ AI Model Quality & Faithfulness")
    st.markdown("**From `GLD_AI_AUDIT_REPORT` — enforces 80% faithfulness SLA**")
    st.markdown("---")

    with st.spinner("Loading audit data..."):
        df_audit = load_ai_audit_report()

    if df_audit.empty:
        st.info("No audit data yet. Trigger `test_cortex_evaluation.py` via CI/CD to populate this table.")
    else:
        avg_confidence  = df_audit['CONFIDENCE_SCORE'].mean()
        avg_faithfulness = df_audit['FAITHFULNESS_SCORE'].mean()
        SLA_THRESHOLD = 0.80

        col1, col2, col3 = st.columns(3)
        col1.metric("Avg Confidence Score",    f"{avg_confidence * 100:.1f}%")
        status = "✅ PASS" if avg_faithfulness >= SLA_THRESHOLD else "❌ FAIL"
        col2.metric("Avg Faithfulness Score",  f"{avg_faithfulness * 100:.1f}%",
                    delta=f"{(avg_faithfulness - SLA_THRESHOLD) * 100:+.1f}% vs SLA")
        col3.metric("Deployment Gate",         status)

        st.markdown("---")

        if avg_faithfulness < SLA_THRESHOLD:
            st.error(f"🚨 **SLA BREACH**: Faithfulness ({avg_faithfulness:.2%}) is below the 80% threshold. CI/CD gate would BLOCK deployment.")
        else:
            st.success(f"✅ **SLA MET**: Faithfulness ({avg_faithfulness:.2%}) exceeds the 80% threshold. CI/CD gate would PASS.")

        st.subheader("Recent Audit Records")
        st.dataframe(
            df_audit,
            use_container_width=True,
            column_config={
                "CONFIDENCE_SCORE":   st.column_config.ProgressColumn("Confidence",   min_value=0.0, max_value=1.0),
                "FAITHFULNESS_SCORE": st.column_config.ProgressColumn("Faithfulness", min_value=0.0, max_value=1.0),
                "AUDIT_TIMESTAMP":    st.column_config.DatetimeColumn("Audited At"),
            }
        )
