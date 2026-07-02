import os 
#MLFLOW
REPO_OWNER = os.getenv("REPO_OWNER")
REPO_NAME = os.getenv("REPO_NAME")
TRACKING_URI = os.getenv("TRACKING_URI")

#MongoDB
DATABASE_NAME = os.getenv("DB_NAME")
MONGODB_URL_KEY = os.getenv("MONGODB_URL")

#Pipeline
PIPELINE_NAME: str = ""
DATA_DIR_NAME: str = "data"
BUCKET_NAME: str = os.getenv("BUCKET_NAME")

#Logging
LOG_DIR: str = "/tmp/logs"

#Data Ingestion
DATA_INGESTION_COLLECTION_NAME: str = os.getenv("COLLECTION_NAME")
DATA_INGESTION_DIR_NAME: str = "raw"

#Data Cleaning
DATA_CLEANING_DIR_NAME: str = "cleaned"

#Data Transformation
DATA_TRANSFORMATION_DIR_NAME: str = "transformed"
SPLIT_TEST_SIZE: float = 0.2