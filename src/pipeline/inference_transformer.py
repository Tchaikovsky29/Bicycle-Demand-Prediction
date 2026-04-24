import argparse
import json
import logging
import os
import pickle
from typing import Dict

import boto3
import mlflow
import httpx
import kserve

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FEATURE_ORDER = [
    "Hour", "Temperature", "Humidity", "Wind speed", "Visibility",
    "Solar Radiation", "Rainfall", "Snowfall", "Seasons", "Holiday",
    "Day", "Month", "Year"
]


class BicycleDemandTransformer(kserve.Model):
    def __init__(self, name: str, predictor_host: str, predictor_protocol: str):
        super().__init__(name)
        self.predictor_host = predictor_host
        self.predictor_protocol = predictor_protocol
        self.encoders = {}
        self.ready = False
        self.load()

    def load(self):
        logger.info("Loading run_info from MinIO...")
        s3 = boto3.client(
            "s3",
            endpoint_url=os.environ["AWS_ENDPOINT_URL"],
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        )
        bucket = os.environ["BUCKET_NAME"]

        run_info_obj = s3.get_object(
            Bucket=bucket,
            Key="data/models/serving/bicycle-demand-predictor/run_info.json"
        )
        run_info = json.loads(run_info_obj["Body"].read())
        run_id = run_info["mlflow_run_id"]
        logger.info(f"Using MLflow run ID: {run_id}")

        os.environ["MLFLOW_TRACKING_USERNAME"] = os.environ["REPO_OWNER"]
        os.environ["MLFLOW_TRACKING_PASSWORD"] = os.environ["DAGSHUB_USER_TOKEN"]
        mlflow.set_tracking_uri(os.environ["TRACKING_URI"])

        local_path = mlflow.artifacts.download_artifacts(
            run_id=run_id,
            artifact_path="encoders/encoders.pkl"
        )
        with open(local_path, "rb") as f:
            self.encoders = pickle.load(f)

        logger.info(f"Loaded encoders for: {list(self.encoders.keys())}")
        self.ready = True

    def preprocess(self, payload: Dict, headers: Dict[str, str] = None) -> Dict:
        """
        Accepts raw user input with categorical string values,
        encodes them and returns v1 instances format for the predictor.
        """
        instances = payload.get("instances", [])
        processed = []

        for instance in instances:
            # Encode categorical columns
            for col, le in self.encoders.items():
                if col in instance:
                    val = instance[col]
                    if val not in list(le.classes_):
                        raise ValueError(
                            f"Unknown value '{val}' for '{col}'. "
                            f"Expected one of: {list(le.classes_)}"
                        )
                    instance[col] = int(le.transform([val])[0])

            # Build feature vector in correct order
            features = [float(instance[col]) for col in FEATURE_ORDER]
            processed.append(features)

        return {"instances": processed}

    def postprocess(self, outputs: Dict, headers: Dict[str, str] = None) -> Dict:
        """
        Squares the sqrt-transformed prediction to get actual bike count.
        """
        predictions = outputs.get("predictions", [])
        results = []
        for pred in predictions:
            raw = pred[0] if isinstance(pred, list) else pred
            bike_count = float(raw) ** 2
            results.append({
                "predicted_bike_count": round(bike_count),
                "raw_prediction": float(raw),
            })

        return {"predictions": results}

    async def predict(self, payload: Dict, headers: Dict[str, str] = None) -> Dict:
        # Call predictor in v2 format
        features = payload["instances"][0]  # already preprocessed list of floats
        
        v2_payload = {
            "inputs": [{
                "name": "float_input",
                "shape": [1, len(features)],
                "datatype": "FP32",
                "data": features
            }]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{self.predictor_host}/v2/models/{self.name}/infer",
                json=v2_payload,
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
        
        # Extract prediction from v2 response
        raw = result["outputs"][0]["data"][0]
        return {"predictions": [raw]}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", default="bicycle-demand-predictor")
    parser.add_argument("--predictor_host", required=False, default=None)
    parser.add_argument("--predictor_protocol", required=False, default="v2")
    args, _ = parser.parse_known_args()

    transformer = BicycleDemandTransformer(
        name=args.model_name,
        predictor_host=args.predictor_host,
        predictor_protocol=args.predictor_protocol,
    )
    kserve.ModelServer().start([transformer])