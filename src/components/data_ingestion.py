from typing import NamedTuple
from kfp import compiler, kubernetes
from kfp.dsl import component, pipeline
from kfp.kubernetes import use_secret_as_env

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

    from src.configuration.aws_connection import buckets
    from src.entity.config_entity import DataIngestionConfig
    from src.exception import MyException
    from src.logger import logging
    from src.data_access.data import Data

    try:
        config = DataIngestionConfig()
        bucket = buckets()

        logging.info("Pulling collection from MongoDB...")
        my_data = Data()
        dataframe, hash_value = my_data.export_collection_as_dataframe(
            database_name=config.database_name,
            collection_name=config.collection_name
        )
        logging.info(f"Pulled {dataframe.shape[0]} rows, hash: {hash_value}")

        s3_path = os.path.join(config.folder_name, f"{hash_value}.parquet")
        meta_path = s3_path.replace(".parquet", ".meta.json")

        exists = bucket.path_exists_in_s3(
            bucket_name=config.bucket_name,
            path=s3_path
        )

        if exists:
            logging.info(f"Dataset already exists at {s3_path}. Skipping upload.")
        else:
            logging.info(f"New dataset detected. Uploading to {s3_path}...")

            bucket.upload_file(
                bucket=config.bucket_name,
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
                bucket=config.bucket_name,
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
        raise MyException(e, sys)


# @pipeline(
#     name="data-ingestion-pipeline",
#     description="Ingests data from MongoDB into S3, skipping upload if dataset already exists."
# )
# def data_ingestion_pipeline():
#     ingest = data_ingestion_component()
#     ingest.set_caching_options(False)
#     use_secret_as_env(
#         ingest,
#         secret_name="app-secrets",
#         secret_key_to_env={
#             "MONGODB_URL": "MONGODB_URL",
#             "DB_NAME": "DB_NAME",
#             "COLLECTION_NAME": "COLLECTION_NAME",
#             "BUCKET_NAME": "BUCKET_NAME",
#             "AWS_ENDPOINT_URL": "AWS_ENDPOINT_URL",
#             "AWS_ACCESS_KEY_ID": "AWS_ACCESS_KEY_ID",
#             "AWS_SECRET_ACCESS_KEY": "AWS_SECRET_ACCESS_KEY",
#             "REPO_OWNER": "REPO_OWNER",
#             "REPO_NAME": "REPO_NAME",
#             "TRACKING_URI": "TRACKING_URI",
#         }
#     )
#     kubernetes.set_image_pull_policy(ingest, "Always")

# if __name__ == "__main__":
#     compiler.Compiler().compile(
#         data_ingestion_pipeline,
#         "data_ingestion_pipeline.yaml"
#     )