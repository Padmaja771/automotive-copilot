# Automotive Intelligence Copilot

An AI-powered Insights Copilot tailored for the Automotive industry, leveraging Snowflake Cortex AI to synthesize vehicle documents, diagnostic logs, and service records.

## Project Structure

- `src/`: Core logic, Snowflake integration, and data pipelines.
- `ui/`: Streamlit dashboard and UI code.
- `infrastructure/`: Production-ready AWS (Terraform) and Snowflake (SQL) orchestration.
- `data/`: Sample synthetic data for testing.
- `notebooks/`: Jupyter Notebooks for experimentation.
- `tests/`: Project tests.

## Architecture
This project implements a state-of-the-art **Event-Driven AI Pipeline**:
1. **AWS S3**: Acts as the landing zone for vehicle documents.
2. **AWS Lambda**: Detects new uploads and registers them in Snowflake via Secrets Manager.
3. **Snowflake Cortex**: Uses `PARSE_DOCUMENT` (LLM-native parsing) to vectorize and chunk PDFs.
4. **Streamlit**: A premium RAG interface for mechanics to chat with vehicle intelligence.


## Setup Instructions

1. Run the `src/setup.sql` in your Snowflake environment to set up the data models.
2. Install Python dependencies: `pip install -r requirements.txt`
3. Set up your Snowflake `.env` or `.streamlit/secrets.toml` with credentials.
4. Run the Streamlit app: `streamlit run ui/app.py`
