from kfp import kubernetes
import kfp
from kfp.dsl import pipeline
from kfp.kubernetes import use_secret_as_env
from src.components.data_ingestion import data_ingestion_component
from src.components.data_validation import data_validation_component
from src.components.data_cleaning import data_cleaning_component
from src.components.data_transformation import data_transformation_component

SECRET_KEYS = {
    "MONGODB_URL": "MONGODB_URL",
    "DB_NAME": "DB_NAME",
    "COLLECTION_NAME": "COLLECTION_NAME",
    "BUCKET_NAME": "BUCKET_NAME",
    "AWS_ENDPOINT_URL": "AWS_ENDPOINT_URL",
    "AWS_ACCESS_KEY_ID": "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY": "AWS_SECRET_ACCESS_KEY",
    "REPO_OWNER": "REPO_OWNER",
    "REPO_NAME": "REPO_NAME",
    "TRACKING_URI": "TRACKING_URI",
}

def apply_secrets(task):
    return use_secret_as_env(task, secret_name="app-secrets", secret_key_to_env=SECRET_KEYS)

def configure_task(task):
    """Applies common configuration to every task."""
    apply_secrets(task)
    kubernetes.set_image_pull_policy(task, "Always")
    return task

@pipeline(
    name="training-pipeline",
    description="Runs the training pipeline for bicycle demand prediction"
)
def training_pipeline():
    ingest = data_ingestion_component()
    ingest.set_caching_options(False)
    configure_task(ingest)

    validate = data_validation_component(
        meta_path=ingest.outputs["meta_path"]
    )
    configure_task(validate)

    clean = data_cleaning_component(
        s3_path=ingest.outputs["s3_path"],
        validation_status=validate.outputs["validation_status"],
        message=validate.outputs["message"]
    )
    configure_task(clean)

    transform = data_transformation_component(
        s3_path = clean.outputs["s3_path"]
    )
    configure_task(transform)

if __name__ == "__main__":
    client = kfp.Client(host="http://localhost:8080")
    client.upload_pipeline_from_pipeline_func(
        training_pipeline,
        pipeline_name="training-pipeline"
    )