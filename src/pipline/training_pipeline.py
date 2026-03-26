from kfp import kubernetes, dsl
import kfp
from kfp.dsl import pipeline
from kfp.kubernetes import use_secret_as_env
from src.components.data_ingestion import data_ingestion_component
from src.components.data_validation import data_validation_component
from src.components.data_cleaning import data_cleaning_component
from src.components.data_transformation import data_transformation_component
from src.components.model_evaluation import model_evaluation_component
from src.components.model_trainer import model_training_component
from src.components.model_pusher import model_pusher_component

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
    "DAGSHUB_USER_TOKEN": "DAGSHUB_USER_TOKEN"
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
    ingest = data_ingestion_component(kfp_run_id=dsl.PIPELINE_JOB_ID_PLACEHOLDER)
    ingest.set_caching_options(False)
    configure_task(ingest)

    validate = data_validation_component(
        meta_path=ingest.outputs["meta_path"],
        kfp_run_id=dsl.PIPELINE_JOB_ID_PLACEHOLDER
    )
    configure_task(validate)

    clean = data_cleaning_component(
        s3_path=ingest.outputs["s3_path"],
        validation_status=validate.outputs["validation_status"],
        message=validate.outputs["message"],
        kfp_run_id=dsl.PIPELINE_JOB_ID_PLACEHOLDER
    )
    configure_task(clean)

    transform = data_transformation_component(
        s3_path = clean.outputs["s3_path"],
        kfp_run_id=dsl.PIPELINE_JOB_ID_PLACEHOLDER
    )
    configure_task(transform)

    trainer = model_training_component(
        train_path=transform.outputs["train_path"],
        mlflow_run_id=transform.outputs["mlflow_run_id"],
        kfp_run_id=dsl.PIPELINE_JOB_ID_PLACEHOLDER
    )
    configure_task(trainer)

    evaluate = model_evaluation_component(
        test_path=transform.outputs["test_path"],
        model_s3_path=trainer.outputs["model_s3_path"],
        mlflow_run_id=trainer.outputs["mlflow_run_id"],
        kfp_run_id=dsl.PIPELINE_JOB_ID_PLACEHOLDER
    )
    configure_task(evaluate)

    pusher = model_pusher_component(
        is_model_accepted=evaluate.outputs["is_model_accepted"],
        test_path=transform.outputs["test_path"],
        model_s3_path=trainer.outputs["model_s3_path"],
        new_model_r2=evaluate.outputs["r2"],
        kfp_run_id=dsl.PIPELINE_JOB_ID_PLACEHOLDER
    )
    configure_task(pusher)

if __name__ == "__main__":
    client = kfp.Client(host="http://localhost:8080")
    client.upload_pipeline_from_pipeline_func(
        training_pipeline,
        pipeline_name="training-pipeline"
    )