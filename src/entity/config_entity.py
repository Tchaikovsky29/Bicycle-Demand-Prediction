import os
from src.constants import *
from dataclasses import dataclass
from datetime import datetime

TIMESTAMP: str = datetime.now().strftime("%Y_%m_%d_%H")

@dataclass
class TrainingPipelineConfig:
    pipeline_name: str = PIPELINE_NAME
    artifact_dir: str = os.path.join(ARTIFACT_DIR, TIMESTAMP)
    data_dir: str = DATA_DIR_NAME
    timestamp: str = TIMESTAMP

training_pipeline_config: TrainingPipelineConfig = TrainingPipelineConfig()

@dataclass
class DataIngestionConfig:
    database_name: str = DATABASE_NAME
    folder_name: str = os.path.join(training_pipeline_config.data_dir, DATA_INGESTION_DIR_NAME)
    data_file_path: str = os.path.join(folder_name, DATA_FILE_NAME)
    collection_name:str = DATA_INGESTION_COLLECTION_NAME
    artifact_path: str = os.path.join(training_pipeline_config.artifact_dir, DATA_INGESTION_DIR_NAME, DATA_INGESTION_ARTIFACT_NAME)