import json
import time
import sys
import os
from fastapi.testclient import TestClient

# Add project root to path so we can import the app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app

client = TestClient(app)

def run_benchmark(experiment_id: str = None):
    print("\n" + "="*60)
    print(f"🚀 STARTING EVALUATION | Experiment: {experiment_id or 'BASELINE'}")
    print("="*60 + "\n")

    # Load Golden Dataset
    eval_dir = os.path.dirname(__file__)
    with open(os.path.join(eval_dir, "golden_dataset.json"), "r") as f:
        cases = json.load(f)

    results = []
    
    for case in cases:
        print(f"Testing {case['id']}...")
        
        start_time = time.time()
        response = client.post(
            "/api/v1/agent/query",
            json={
                "question": case["question"],
                "vin": case["vin"],
                "provider": "SNOWFLAKE",
                "experiment_id": experiment_id
            },
            headers={"x-api-key": "super_secret_enterprise_key_2026"}
        )
        latency = time.time() - start_time
        
        if response.status_code != 200:
            results.append({"id": case["id"], "success": False})
            continue

        data = response.json()
        conf = data["diagnostic_confidence_score"]
        success = conf >= case["min_confidence"]
        
        results.append({
            "id": case["id"],
            "success": success,
            "latency": latency,
            "confidence": conf
        })

    # Summary Report
    passed = sum(1 for r in results if r["success"])
    total = len(results)
    accuracy = (passed/total)*100
    avg_latency = sum(r.get('latency', 0) for r in results) / total
    
    print("-" * 60)
    print(f"RESULTS FOR {experiment_id or 'BASELINE'}:")
    print(f"  ACCURACY    : {accuracy:.1f}%")
    print(f"  AVG LATENCY : {avg_latency:.2f}s")
    print("-" * 60 + "\n")
    return {"accuracy": accuracy, "latency": avg_latency}

if __name__ == "__main__":
    # Run A/B Comparison
    baseline = run_benchmark(experiment_id=None)
    challenger = run_benchmark(experiment_id="EXP_002_OPENAI_V2")
    
    print("🏁 FINAL A/B COMPARISON REPORT")
    print(f"Baseline (Snowflake V2) Accuracy: {baseline['accuracy']}%")
    print(f"Challenger (OpenAI V2) Accuracy: {challenger['accuracy']}%")
    
    # 💥 EVALUATION GATING: Fail the build if performance drops below SLA
    ACCURACY_THRESHOLD = 80.0
    if baseline['accuracy'] < ACCURACY_THRESHOLD:
        print(f"❌ ERROR: Baseline accuracy ({baseline['accuracy']}%) is below the production SLA ({ACCURACY_THRESHOLD}%).")
        sys.exit(1)

    if challenger['accuracy'] >= baseline['accuracy']:
        print("🏆 RESULT: Challenger is performing better or equal to Baseline!")
    else:
        print("💡 RESULT: Baseline remains superior.")
    
    sys.exit(0)
