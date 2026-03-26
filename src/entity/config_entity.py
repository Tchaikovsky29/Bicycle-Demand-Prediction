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
    transformation: tuple = ("sqrt", 0.5)

@dataclass
class ModelTrainingConfig:
    folder_name: str = os.path.join(training_pipeline_config.data_dir, "models")
    n_estimators: int = 1000
    max_depth: int = 6
    min_samples_split: int = 10
    learning_rate: float = 0.1
    loss: str = 'huber'

@dataclass
class ModelEvaluationConfig:
    min_r2_score: float = 0.8

class ModelPusherConfig:
    folder_name: str = os.path.join(training_pipeline_config.data_dir, "models", "production")