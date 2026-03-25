from typing import NamedTuple
from kfp.dsl import component

@component(
    base_image="tchaikovsky29/env-base-image:latest",
)
def data_ingestion_component() -> NamedTuple("IngestOutput", [
    ("s3_path", str),
    ("meta_path", str),
    ("data_hash", str)
]):
    """
    Pulls the full collection from MongoDB, computes a SHA-256 hash of
    the DataFrame contents, and uploads it to S3 if not already present.
    Always returns the S3 path and metadata path for downstream components.
    """
    import json
    import os
    import sys
    from collections import namedtuple
    from datetime import datetime, timezone
    from src.utils.main_utils import generate_dataset_hash
    from src.configuration.aws_connection import buckets
    from src.entity.config_entity import DataIngestionConfig
    from src.exception import MyException
    from src.logger import logging
    from src.data_access.data import Data
    from src.constants import BUCKET_NAME

    try:
        config = DataIngestionConfig()
        bucket = buckets()

        logging.info("Pulling collection from MongoDB...")
        my_data = Data()
        dataframe = my_data.export_collection_as_dataframe(
            database_name=config.database_name,
            collection_name=config.collection_name
        )
        hash_value = generate_dataset_hash(dataframe)
        logging.info(f"Pulled {dataframe.shape[0]} rows, hash: {hash_value}")

        s3_path = os.path.join(config.folder_name, f"{hash_value}.parquet")
        meta_path = s3_path.replace(".parquet", ".meta.json")

        exists = bucket.path_exists_in_s3(
            bucket_name= BUCKET_NAME,
            path=s3_path
        )

        if exists:
            logging.info(f"Dataset already exists at {s3_path}. Skipping upload.")
        else:
            logging.info(f"New dataset detected. Uploading to {s3_path}...")

            bucket.upload_file(
                bucket= BUCKET_NAME,
                key=s3_path,
                body=dataframe.to_parquet(index=False)
            )

            meta = {
                "hash": hash_value,
                "s3_path": s3_path,
                "rows": dataframe.shape[0],
                "columns": dataframe.shape[1],
                "column_names": list(dataframe.columns),
                "database": config.database_name,
                "collection": config.collection_name,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }
            bucket.upload_file(
                bucket= BUCKET_NAME,
                key=meta_path,
                body=json.dumps(meta, indent=2).encode()
            )
            logging.info(f"Upload complete. Metadata saved to {meta_path}")

        IngestOutput = namedtuple("IngestOutput", ["s3_path", "meta_path", "data_hash"])
        return IngestOutput(
            s3_path=s3_path,
            meta_path=meta_path,
            data_hash=hash_value
        )

    except Exception as e:
        logging.error(f"Data ingestion error: {e}")
        raise MyException(e, sys)