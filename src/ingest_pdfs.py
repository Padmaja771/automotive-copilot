"""
ingest_pdfs.py
--------------
Scans the /data/raw_manuals/ folder for PDF files,
uploads them to a Snowflake internal Stage, and
then triggers the Cortex PARSE_DOCUMENT pipeline.

Usage:
    python3 src/ingest_pdfs.py
"""

import os
import glob
from dotenv import load_dotenv
from snowflake.snowpark import Session

load_dotenv()

def create_session():
    return Session.builder.configs({
        "account":   os.getenv("SNOWFLAKE_ACCOUNT"),
        "user":      os.getenv("SNOWFLAKE_USER"),
        "password":  os.getenv("SNOWFLAKE_PASSWORD"),
        "role":      os.getenv("SNOWFLAKE_ROLE", "CORTEX_DEV_ROLE"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "AI_PROJECT_WH"),
        "database":  os.getenv("SNOWFLAKE_DATABASE", "AI_PROJECT_DB"),
        "schema":    os.getenv("SNOWFLAKE_SCHEMA", "STAGING"),
    }).create()


def upload_pdfs(session: Session, pdf_folder: str):
    """Upload all PDFs from local folder to Snowflake internal stage."""
    pdf_files = glob.glob(os.path.join(pdf_folder, "*.pdf"))

    if not pdf_files:
        print(f"⚠️  No PDF files found in '{pdf_folder}'.")
        print("   Please place your vehicle manual PDFs there and re-run.")
        return []

    print(f"📂 Found {len(pdf_files)} PDF(s). Uploading to @MANUALS_STAGE...")
    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        print(f"   ⬆️  Uploading: {filename}")
        session.sql(f"PUT 'file://{os.path.abspath(pdf_path)}' @MANUALS_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE").collect()
    
    print("✅ All files uploaded successfully.\n")
    return pdf_files


def refresh_stage_directory(session: Session):
    """Refresh stage metadata so METADATA$FILENAME is available."""
    session.sql("ALTER STAGE MANUALS_STAGE REFRESH").collect()
    print("🔄 Stage directory refreshed.\n")


def run_parse_pipeline(session: Session):
    """Trigger the Cortex PARSE_DOCUMENT INSERT pipeline."""
    print("🧠 Running Cortex PARSE_DOCUMENT pipeline...")
    
    try:
        result = session.sql("""
            INSERT INTO VEHICLE_MANUALS_PARSED (source_file, vin_reference, chunk_text, chunk_index)
            SELECT 
                METADATA$FILENAME as source_file,
                SPLIT_PART(METADATA$FILENAME, '_', 1) as vin_reference,
                f.value AS chunk_text,
                f.index AS chunk_index
            FROM @MANUALS_STAGE,
            LATERAL FLATTEN(
                INPUT => SNOWFLAKE.CORTEX.PARSE_DOCUMENT(
                    @MANUALS_STAGE,
                    METADATA$FILENAME,
                    {'mode': 'LAYOUT'}
                ):content
            ) f
            WHERE METADATA$FILENAME LIKE '%.pdf'
        """).collect()

        print(f"✅ PDF parsing complete!")
    except Exception as e:
        print(f"❌ Parse pipeline failed: {e}")
        raise


def verify_output(session: Session):
    """Preview the parsed content from the database."""
    print("\n📋 Parsed Content Preview:")
    print("-" * 60)
    df = session.sql("""
        SELECT source_file, vin_reference, chunk_index, LEFT(chunk_text, 150) as preview
        FROM VEHICLE_MANUALS_PARSED 
        ORDER BY manual_id
        LIMIT 10
    """).to_pandas()
    print(df.to_string(index=False))
    print("-" * 60)


if __name__ == "__main__":
    # Paths are relative to the project root
    PDF_FOLDER = os.path.join(os.path.dirname(__file__), "..", "data", "raw_manuals")
    
    print("=" * 60)
    print("🏎️  Automotive Copilot — PDF Ingestion Pipeline")
    print("=" * 60)
    
    session = create_session()
    print(f"✅ Connected to Snowflake as {os.getenv('SNOWFLAKE_USER')}\n")
    
    uploaded = upload_pdfs(session, PDF_FOLDER)
    
    if uploaded:
        refresh_stage_directory(session)
        run_parse_pipeline(session)
        verify_output(session)
