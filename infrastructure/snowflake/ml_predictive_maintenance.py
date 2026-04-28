import sys
import os
import logging
from snowflake.snowpark import Session
import snowflake.snowpark.functions as F

# Snowflake ML imports
from snowflake.ml.modeling.ensemble import RandomForestClassifier
from snowflake.ml.modeling.metrics import accuracy_score, precision_score
from snowflake.ml.registry import Registry

logger = logging.getLogger("PredictiveMaintenance")
logging.basicConfig(level=logging.INFO)

def train_and_deploy_model(session: Session):
    """
    Standard: Predictive Modeling & Scoring using Snowpark ML.
    Trains a Random Forest classifier to predict vehicle failure risk.
    Deploys it to the Snowflake Model Registry for in-database scoring.
    """
    logger.info("Starting Predictive Maintenance ML Pipeline...")

    # 1. Feature Engineering (Data Prep)
    # We use the Silver Telematics layer as our training dataset
    logger.info("Loading training data from Silver layer...")
    df = session.table("AI_PROJECT_DB.SILVER.SLV_TELEMATICS")

    # Create Synthetic Labels for the sake of the demonstration
    # In reality, this would be a historical 'has_failed_within_30_days' column
    feature_df = df.with_column(
        "IS_AT_RISK",
        F.when(F.col("ENGINE_TEMPERATURE_CELSIUS") > 110.0, 1).otherwise(0)
    ).with_column(
        "TEMP_VARIANCE",
        F.col("ENGINE_TEMPERATURE_CELSIUS") * 1.5 # Dummy feature engineering
    )

    # 2. Train-Test Split
    train_df, test_df = feature_df.random_split(weights=[0.8, 0.2], seed=42)

    # 3. Model Training (Executed on Snowflake Compute!)
    logger.info("Training Random Forest Classifier on Snowflake compute...")
    rf_model = RandomForestClassifier(
        input_cols=["ENGINE_TEMPERATURE_CELSIUS", "TEMP_VARIANCE"],
        label_cols=["IS_AT_RISK"],
        output_cols=["PREDICTED_RISK_CLASS"],
        n_estimators=100,
        random_state=42
    )
    
    # Fit the model
    rf_model.fit(train_df)

    # 4. Model Scoring & Evaluation
    logger.info("Scoring model...")
    predictions = rf_model.predict(test_df)
    
    acc = accuracy_score(df=predictions, y_true_col_names="IS_AT_RISK", y_pred_col_names="PREDICTED_RISK_CLASS")
    logger.info(f"Model Accuracy: {acc * 100:.2f}%")

    # 5. Model Deployment (Snowflake Model Registry)
    logger.info("Deploying model to Snowflake Registry...")
    registry = Registry(session=session, database_name="AI_PROJECT_DB", schema_name="STAGING")
    
    try:
        model_ref = registry.log_model(
            model=rf_model,
            model_name="PREDICTIVE_MAINTENANCE_RF",
            version_name="v1",
            comment="Predicts critical component failure risk based on engine telemetry."
        )
        logger.info("Model deployed successfully! Ready for SQL inference.")
    except Exception as e:
        logger.warning(f"Model logging skipped (might already exist): {e}")

if __name__ == "__main__":
    # Add project root to path so we can import the session manager
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "applications", "api")))
    from app.core.snowflake_session import get_snowpark_session
    
    session = get_snowpark_session()
    if session:
        train_and_deploy_model(session)
    else:
        logger.error("Failed to connect to Snowflake. Please check .env credentials.")
