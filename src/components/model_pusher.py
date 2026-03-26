from kfp.dsl import component
from typing import NamedTuple


@component(
    base_image="tchaikovsky29/env-base-image:latest"
)
def model_pusher_component(
    model_s3_path: str,
    test_path: str,
    new_model_r2: float,
    is_model_accepted: bool,
    kfp_run_id: str
) -> NamedTuple("PusherOutput", [
    ("pushed", bool),
    ("prod_model_path", str),
]):
    """
    Fetches the current production model if one exists, evaluates it on
    the same test set as the new model, and compares R2 scores. If the
    new model is better, it is copied to the production path in S3 and
    the result is logged to the existing MLflow run.
    """
    import sys
    from collections import namedtuple
    from io import BytesIO
    import os

    import joblib
    import pandas as pd
    from sklearn.metrics import r2_score

    from src.configuration.aws_connection import buckets
    from src.entity.config_entity import ModelPusherConfig
    from src.exception import MyException
    from src.logger import get_logger
    from src.constants import BUCKET_NAME

    try:
        os.environ["KFP_RUN_ID"] = kfp_run_id
        logging = get_logger()
        config = ModelPusherConfig()
        bucket = buckets()

        prod_model_path = os.path.join(config.folder_name, "model.pkl")
        prod_r2 = 0.0

        # Check if a production model exists
        prod_exists = bucket.path_exists_in_s3(
            bucket_name=BUCKET_NAME,
            path=prod_model_path
        )

        if not prod_exists:
            # No production model yet — push unconditionally
            logging.info("No production model found. Pushing new model to production...")
            pushed = True
        elif not is_model_accepted:
            logging.info("New model did not meet acceptance criteria. Skipping push.")
            pushed = False
        else:
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
            # Evaluate production model on same test set
            logging.info(f"Loading production model from {prod_model_path}...")
            prod_bytes = bucket.download_file(
                bucket=BUCKET_NAME,
                key=prod_model_path,
                as_object=True
            )
            prod_model = joblib.load(BytesIO(prod_bytes))
            prod_r2 = float(r2_score(y_test, prod_model.predict(X_test)))
            logging.info(f"Production model R2: {prod_r2:.4f} | New model R2: {new_model_r2:.4f}")

            pushed = new_model_r2 > prod_r2
            if pushed:
                logging.info("New model outperforms production model. Pushing to production...")
            else:
                logging.info("New model does not outperform production model. Skipping push.")
            
        if pushed:
            new_model_bytes = bucket.download_file(
                bucket=BUCKET_NAME,
                key=model_s3_path,
                as_object=True
                )
            bucket.upload_file(
                bucket=BUCKET_NAME,
                key=prod_model_path,
                body=new_model_bytes
            )
            logging.info(f"New model pushed to production at {prod_model_path}")
            
        PusherOutput = namedtuple("PusherOutput", ["pushed", "prod_model_path"])
        return PusherOutput(
            pushed=pushed,
            prod_model_path=prod_model_path if pushed else "",
        )

    except Exception as e:
        raise MyException(e, sys)