from typing import NamedTuple
from kfp.dsl import component

@component(
    base_image="tchaikovsky29/env-base-image:latest",
)
def data_transformation_component(
    s3_path: str, kfp_run_id: str
) -> NamedTuple("TransformationOutput", [
    ("train_path", str),
    ("test_path", str),
    ("mlflow_run_id", str)
]):
    """
    Loads cleaned parquet from S3 and performs transformation steps:
      - Label encodes all columns
      - Applies sqrt transform to Rented Bike Count and Wind speed
      - Splits into train/test sets
      - Uploads combined train and test parquets to S3
    """
    import sys
    from collections import namedtuple
    from io import BytesIO
    import os
    import dagshub
    import mlflow
    import pandas as pd
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import LabelEncoder
    from src.utils.main_utils import generate_dataset_hash
    from src.configuration.aws_connection import buckets
    from src.entity.config_entity import DataTransformationConfig
    from src.exception import MyException
    from src.logger import get_logger
    from src.constants import BUCKET_NAME, REPO_OWNER, REPO_NAME

    try:
        os.environ["KFP_RUN_ID"] = kfp_run_id
        logging = get_logger()
        config = DataTransformationConfig()
        bucket = buckets()

        logging.info(f"Downloading cleaned dataset from {s3_path}...")
        clean_bytes = bucket.download_file(
            bucket=BUCKET_NAME,
            key=s3_path,
            as_object=True
        )
        df = pd.read_parquet(BytesIO(clean_bytes))
        logging.info(f"Loaded cleaned dataset: {df.shape[0]} rows, {df.shape[1]} columns")

        # Label encode all columns
        df = df.apply(LabelEncoder().fit_transform)
        logging.info("Label encoding complete.")

        # Apply transforms
        df["Rented Bike Count"] = df["Rented Bike Count"] ** config.transformation[1]
        df["Wind speed"] = df["Wind speed"] ** config.transformation[1]
        logging.info("Transforms applied to Rented Bike Count and Wind speed.")

        # Split features and target
        X = df.drop("Rented Bike Count", axis=1)
        y = df["Rented Bike Count"]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=config.test_size, random_state=42
        )
        logging.info(f"Train/test split: {len(X_train)} train rows, {len(X_test)} test rows")

        # Compute hash from transformed training set
        transform_hash = generate_dataset_hash(X_train)
        base_path = f"{config.folder_name}/{transform_hash}"
        train_path = f"{base_path}/train.parquet"
        test_path = f"{base_path}/test.parquet"

        # Combine X and y for storage
        train_df = X_train.copy()
        train_df["Rented Bike Count"] = y_train.values
        test_df = X_test.copy()
        test_df["Rented Bike Count"] = y_test.values

        logging.info(f"Uploading transformed datasets to {base_path}...")
        bucket.upload_file(
            bucket=BUCKET_NAME,
            key=train_path,
            body=train_df.to_parquet(index=False)
        )
        bucket.upload_file(
            bucket=BUCKET_NAME,
            key=test_path,
            body=test_df.to_parquet(index=False)
        )
        logging.info("Upload complete.")

        # Start MLflow run and log transformation params
        os.environ["DAGSHUB_USER_TOKEN"] = os.getenv("DAGSHUB_USER_TOKEN")
        dagshub.auth.add_app_token(os.getenv("DAGSHUB_USER_TOKEN"))
        dagshub.init(repo_owner=REPO_OWNER, repo_name=REPO_NAME, mlflow=True)
        with mlflow.start_run() as run:
            mlflow.log_params({
                "encoding": "LabelEncoder",
                "target_transform": config.transformation[0],
                "wind_speed_transform": config.transformation[0],
                "test_size": config.test_size,
                "random_state": 42,
                "train_rows": len(X_train),
                "test_rows": len(X_test),
                "n_features": X_train.shape[1],
            })
            run_id = run.info.run_id
            logging.info(f"Started MLflow run: {run_id}")
 
        TransformationOutput = namedtuple("TransformationOutput", [
            "train_path", "test_path", "mlflow_run_id"
        ])
        return TransformationOutput(
            train_path=train_path,
            test_path=test_path,
            mlflow_run_id=run_id
        )

    except Exception as e:
        raise MyException(e, sys)