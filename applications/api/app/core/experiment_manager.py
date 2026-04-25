import yaml
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger("AI_Experiment_Manager")

class ExperimentManager:
    """Enterprise-grade A/B testing and experiment tracking system."""
    
    def __init__(self):
        self.config_path = os.path.join(os.path.dirname(__file__), "..", "..", "experiments", "config.yaml")
        self.runs_dir = os.path.join(os.path.dirname(__file__), "..", "..", "experiments", "runs")

    def get_experiment_config(self, experiment_id: str) -> dict:
        """Fetches the A/B test parameters for a specific experiment ID."""
        try:
            with open(self.config_path, 'r') as file:
                data = yaml.safe_load(file)
            
            for exp in data.get("experiments", []):
                if exp["id"] == experiment_id:
                    return exp
            
            logger.warning(f"Experiment ID {experiment_id} not found. Falling back to default.")
            return None
        except Exception as e:
            logger.error(f"Failed to load experiment registry: {e}")
            return None

    def log_run(self, experiment_id: str, vin: str, metrics: dict):
        """Simulates MLflow / Weights & Biases behavior by persisting run data."""
        run_file = os.path.join(self.runs_dir, f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        payload = {
            "experiment_id": experiment_id,
            "timestamp": str(datetime.now()),
            "vin": vin,
            "metrics": metrics
        }
        
        try:
            with open(run_file, 'w') as f:
                json.dump(payload, f, indent=2)
            logger.info(f"📁 Experiment Run Versioned & Logged: {os.path.basename(run_file)}")
        except Exception as e:
            logger.error(f"Failed to log experiment run: {e}")
