import os
from src.constants import *
from dataclasses import dataclass
from datetime import datetime

TIMESTAMP: str = datetime.now().strftime("%Y_%m_%d_%H")

@dataclass
class TrainingPipelineConfig:
    pipeline_name: str = PIPELINE_NAME
    data_dir: str = DATA_DIR_NAME

training_pipeline_config: TrainingPipelineConfig = TrainingPipelineConfig()

@dataclass
class DataIngestionConfig:
    database_name: str = DATABASE_NAME
    bucket_name: str = BUCKET_NAME
    folder_name: str = os.path.join(training_pipeline_config.data_dir, DATA_INGESTION_DIR_NAME)
    collection_name:str = DATA_INGESTION_COLLECTION_NAME