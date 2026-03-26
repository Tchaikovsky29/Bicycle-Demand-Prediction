from typing import NamedTuple
from kfp.dsl import component


@component(
    base_image="tchaikovsky29/env-base-image:latest",
)
def model_evaluation_component(
    test_path: str,
    model_s3_path: str,
    mlflow_run_id: str,
    kfp_run_id: str
) -> NamedTuple("EvaluationOutput", [
    ("rmse", float),
    ("mae", float),
    ("r2", float),
    ("is_model_accepted", bool),
]):
    """
    Loads test parquet and trained model from S3, evaluates the model,
    logs metrics to the existing MLflow run, and determines if the
    model meets the acceptance threshold.
    """
    import sys
    from collections import namedtuple
    from io import BytesIO
    import os
    import dagshub
    import joblib
    import mlflow
    import numpy as np
    import pandas as pd
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    from src.configuration.aws_connection import buckets
    from src.entity.config_entity import ModelEvaluationConfig
    from src.exception import MyException
    from src.logger import get_logger
    from src.constants import BUCKET_NAME, REPO_OWNER, REPO_NAME

    try:
        os.environ["KFP_RUN_ID"] = kfp_run_id
        logging = get_logger()
        config = ModelEvaluationConfig()
        bucket = buckets()

        # Load test dataset
        logging.info(f"Downloading test dataset from {test_path}...")
        test_bytes = bucket.download_file(
            bucket=BUCKET_NAME,
            key=test_path,
            as_object=True
        )
        test_df = pd.read_parquet(BytesIO(test_bytes))
        X_test = test_df.drop("Rented Bike Count", axis=1)
        y_test = test_df["Rented Bike Count"]
        logging.info(f"Loaded test dataset: {X_test.shape[0]} rows")

        # Load model
        logging.info(f"Downloading model from {model_s3_path}...")
        model_bytes = bucket.download_file(
            bucket=BUCKET_NAME,
            key=model_s3_path,
            as_object=True
        )
        model = joblib.load(BytesIO(model_bytes))
        logging.info("Model loaded successfully.")

        # Evaluate
        y_pred = model.predict(X_test)
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        mae = float(mean_absolute_error(y_test, y_pred))
        r2 = float(r2_score(y_test, y_pred))
        logging.info(f"Evaluation metrics — RMSE: {rmse:.4f}, MAE: {mae:.4f}, R2: {r2:.4f}")

        is_model_accepted = r2 >= config.min_r2_score
        logging.info(f"Model accepted: {is_model_accepted} (threshold: {config.min_r2_score})")

        # Resume MLflow run and log metrics
        os.environ["DAGSHUB_USER_TOKEN"] = os.getenv("DAGSHUB_USER_TOKEN")
        dagshub.auth.add_app_token(os.getenv("DAGSHUB_USER_TOKEN"))
        dagshub.init(repo_owner=REPO_OWNER, repo_name=REPO_NAME, mlflow=True)
        with mlflow.start_run(run_id=mlflow_run_id):
            mlflow.log_metrics({
                "rmse": rmse,
                "mae": mae,
                "r2": r2,
            })
            mlflow.set_tag("model_accepted", str(is_model_accepted))
            logging.info(f"Logged metrics to MLflow run {mlflow_run_id}")

        EvaluationOutput = namedtuple("EvaluationOutput", ["rmse", "mae", "r2", "is_model_accepted"])
        return EvaluationOutput(
            rmse=rmse,
            mae=mae,
            r2=r2,
            is_model_accepted=is_model_accepted,
        )

    except Exception as e:
        raise MyException(e, sys)