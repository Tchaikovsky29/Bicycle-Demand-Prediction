import hashlib
from typing import NamedTuple
from kfp.dsl import component


@component(
    base_image="tchaikovsky29/env-base-image:latest",
)
def data_transformation_component(
    s3_path: str,
) -> NamedTuple("TransformationOutput", [
    ("train_path", str),
    ("test_path", str)
]):
    """
    Loads cleaned parquet from S3 and performs transformation steps:
      - Label encodes all columns
      - Applies sqrt transform to Rented Bike Count and Wind speed
      - Splits into train/test sets (80/20)
      - Uploads combined train and test parquets to S3
    """
    import sys
    from collections import namedtuple
    from io import BytesIO

    import pandas as pd
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import LabelEncoder
    from src.utils.main_utils import generate_dataset_hash
    from src.configuration.aws_connection import buckets
    from src.entity.config_entity import DataTransformationConfig
    from src.exception import MyException
    from src.logger import logging
    from src.constants import BUCKET_NAME

    try:
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

        # Apply sqrt transforms
        df["Rented Bike Count"] = df["Rented Bike Count"] ** 0.5
        df["Wind speed"] = df["Wind speed"] ** 0.5
        logging.info("Sqrt transforms applied to Rented Bike Count and Wind speed.")

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

        TransformationOutput = namedtuple("TransformationOutput", [
            "train_path", "test_path"
        ])
        return TransformationOutput(
            train_path=train_path,
            test_path=test_path
        )

    except Exception as e:
        raise MyException(e, sys)