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
    folder_name: str = os.path.join(training_pipeline_config.data_dir, DATA_INGESTION_DIR_NAME)
    collection_name:str = DATA_INGESTION_COLLECTION_NAME

@dataclass
class DataValidationConfig:
    schema_file_path: str = 'config/schema.yaml'

@dataclass
class DataCleaningConfig:
    folder_name: str = os.path.join(training_pipeline_config.data_dir, DATA_CLEANING_DIR_NAME)

@dataclass
class DataTransformationConfig:
    folder_name: str = os.path.join(training_pipeline_config.data_dir, DATA_TRANSFORMATION_DIR_NAME)
    test_size: float = SPLIT_TEST_SIZE