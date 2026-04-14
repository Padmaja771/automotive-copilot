# Automotive Intelligence Copilot

An AI-powered Insights Copilot tailored for the Automotive industry, leveraging Snowflake Cortex AI to synthesize vehicle documents, diagnostic logs, and service records.

## Project Structure

- `src/`: Core logic, Snowflake integration, and data pipelines.
- `ui/`: Streamlit dashboard and UI code.
- `data/`: Sample synthetic data for testing.
- `notebooks/`: Jupyter Notebooks for experimentation.
- `tests/`: Project tests.

## Setup Instructions

1. Run the `src/setup.sql` in your Snowflake environment to set up the data models.
2. Install Python dependencies: `pip install -r requirements.txt`
3. Set up your Snowflake `.env` or `.streamlit/secrets.toml` with credentials.
4. Run the Streamlit app: `streamlit run ui/app.py`
