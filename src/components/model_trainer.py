from typing import NamedTuple
from kfp.dsl import component


@component(
    base_image="tchaikovsky29/env-base-image:latest",
)
def model_training_component(
    train_path: str,
    mlflow_run_id: str,
    kfp_run_id: str
) -> NamedTuple("TrainingOutput", [
    ("model_s3_path", str),
    ("mlflow_run_id", str),
]):
    """
    Loads train parquet from S3, trains a GradientBoostingRegressor,
    logs model and params to the existing MLflow run, and uploads
    the model artifact to S3.
    """
    import sys
    from collections import namedtuple
    from io import BytesIO
    import os
    import dagshub
    import joblib
    import mlflow
    import mlflow.sklearn
    import pandas as pd
    from sklearn.ensemble import GradientBoostingRegressor

    from src.configuration.aws_connection import buckets
    from src.entity.config_entity import ModelTrainingConfig
    from src.exception import MyException
    from src.logger import get_logger
    from src.constants import BUCKET_NAME, REPO_OWNER, REPO_NAME

    try:
        os.environ["KFP_RUN_ID"] = kfp_run_id
        logging = get_logger()
        config = ModelTrainingConfig()
        bucket = buckets()

        logging.info(f"Downloading train dataset from {train_path}...")
        train_bytes = bucket.download_file(
            bucket=BUCKET_NAME,
            key=train_path,
            as_object=True
        )
        train_df = pd.read_parquet(BytesIO(train_bytes))
        X_train = train_df.drop("Rented Bike Count", axis=1)
        y_train = train_df["Rented Bike Count"]
        logging.info(f"Loaded train dataset: {X_train.shape[0]} rows, {X_train.shape[1]} features")

        # Train model
        gbr_params = {
            "n_estimators": config.n_estimators,
            "max_depth": config.max_depth,
            "min_samples_split": config.min_samples_split,
            "learning_rate": config.learning_rate,
            "loss": config.loss,
        }
        logging.info(f"Training GradientBoostingRegressor with params: {gbr_params}")
        model = GradientBoostingRegressor(**gbr_params)
        model.fit(X_train, y_train)
        logging.info("Model training complete.")

        # Serialize and upload model to S3
        model_buffer = BytesIO()
        joblib.dump(model, model_buffer)
        model_buffer.seek(0)
        model_s3_path = f"{config.folder_name}/{mlflow_run_id}/model.pkl"
        bucket.upload_file(
            bucket=BUCKET_NAME,
            key=model_s3_path,
            body=model_buffer.read()
        )
        logging.info(f"Model uploaded to {model_s3_path}")

        # Resume MLflow run and log model + params
        os.environ["DAGSHUB_USER_TOKEN"] = os.getenv("DAGSHUB_USER_TOKEN")
        dagshub.auth.add_app_token(os.getenv("DAGSHUB_USER_TOKEN"))
        dagshub.init(repo_owner=REPO_OWNER, repo_name=REPO_NAME, mlflow=True)
        with mlflow.start_run(run_id=mlflow_run_id):
            mlflow.log_params(gbr_params)
            mlflow.sklearn.log_model(model, "model")
            logging.info(f"Logged model and params to MLflow run {mlflow_run_id}")

        TrainingOutput = namedtuple("TrainingOutput", ["model_s3_path", "mlflow_run_id"])
        return TrainingOutput(
            model_s3_path=model_s3_path,
            mlflow_run_id=mlflow_run_id,
        )

    except Exception as e:
        raise MyException(e, sys)