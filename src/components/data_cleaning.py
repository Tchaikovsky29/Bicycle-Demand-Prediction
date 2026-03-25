from typing import NamedTuple
from kfp.dsl import component


@component(
    base_image="tchaikovsky29/env-base-image:latest",
)
def data_cleaning_component(
    s3_path: str, validation_status:bool, message:str
) -> NamedTuple("CleaningOutput", [
    ("s3_path", str)
]):
    """
    Loads raw parquet from S3, performs cleaning steps:
      - Drops rows where Functioning Day == 'No'
      - Drops Functioning Day and Dew point temperature columns
      - Extracts Day, Month, Year from Date and drops Date column
    Uploads cleaned parquet to S3 using a hash of the cleaned contents.
    """
    import sys
    from collections import namedtuple
    from io import BytesIO

    import pandas as pd
    from src.utils.main_utils import generate_dataset_hash
    from src.configuration.aws_connection import buckets
    from src.entity.config_entity import DataCleaningConfig
    from src.exception import MyException
    from src.logger import logging
    from src.constants import BUCKET_NAME

    try:
        if not validation_status:
            logging.error(f"Data validation failed: {message}")
            raise MyException(f"Data validation failed: {message}", sys)
        
        config = DataCleaningConfig()
        bucket = buckets()

        logging.info(f"Downloading raw dataset from {s3_path}...")
        raw_bytes = bucket.download_file(
            bucket=BUCKET_NAME,
            key=s3_path,
            as_object=True
        )
        df = pd.read_parquet(BytesIO(raw_bytes))
        logging.info(f"Loaded raw dataset: {df.shape[0]} rows, {df.shape[1]} columns")

        # Drop non-functioning days
        df = df.drop(df[df["Functioning Day"] == "No"].index)
        logging.info(f"Dropped non-functioning days: {df.shape[0]} rows remaining")

        # Drop unused columns
        df = df.drop(columns=["Functioning Day", "Dew point temperature"])

        # Extract date features
        df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y")
        df["Day"] = df["Date"].dt.day
        df["Month"] = df["Date"].dt.month
        df["Year"] = df["Date"].dt.year
        df = df.drop(columns=["Date"])

        logging.info(f"Cleaned dataset shape: {df.shape[0]} rows, {df.shape[1]} columns")

        # Compute hash and upload
        clean_hash = generate_dataset_hash(df)
        clean_path = f"{config.folder_name}/{clean_hash}.parquet"

        logging.info(f"Uploading cleaned dataset to {clean_path}...")
        bucket.upload_file(
            bucket=BUCKET_NAME,
            key=clean_path,
            body=df.to_parquet(index=False)
        )
        logging.info("Upload complete.")

        CleaningOutput = namedtuple("CleaningOutput", ["s3_path"])
        return CleaningOutput(
            s3_path=clean_path
        )

    except Exception as e:
        raise MyException(e, sys)