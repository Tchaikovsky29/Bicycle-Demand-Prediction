import os
import sys
import subprocess
from pandas import DataFrame
from kfp.dsl import component

from src.entity.config_entity import DataIngestionConfig
from src.entity.artifact_entity import DataIngestionArtifact
from src.exception import MyException
from src.logger import logging
from src.data_access.data import Data


class DataIngestion:
    def __init__(self, data_ingestion_config: DataIngestionConfig = DataIngestionConfig()):
        try:
            self.data_ingestion_config = data_ingestion_config
        except Exception as e:
            raise MyException(e, sys)

    def export_data_into_feature_store(self) -> DataFrame:
        """
        Pull data from MongoDB and save as parquet file
        """

        try:
            logging.info("Importing data from MongoDB")
            my_data = Data()
            dataframe = my_data.export_collection_as_dataframe(
                database_name=self.data_ingestion_config.database_name,
                collection_name=self.data_ingestion_config.collection_name
            )
            logging.info(f"Data shape: {dataframe.shape}")

            os.makedirs(self.data_ingestion_config.folder_name, exist_ok=True)
            file_path = self.data_ingestion_config.data_file_path
            logging.info(f"Saving dataset to {file_path}")

            dataframe.to_parquet(file_path, index=False)
            return dataframe

        except Exception as e:
            logging.error(f"Error saving dataset: {e}")
            raise MyException(e, sys)

    def track_dataset_with_dvc(self):
        """
        Track dataset with DVC and push to remote
        """
        try:
            file_path = self.data_ingestion_config.data_file_path
            logging.info("Tracking dataset with DVC")

            subprocess.run(["dvc","add", file_path], check=True)
            logging.info("Pushing dataset to DVC remote")
            # subprocess.run(["git","add", f"{file_path}.dvc"], check=True)
            # subprocess.run(["git","commit","f", "-m","add ingested data"], check=True)
            subprocess.run(["dvc","push"], check=True)

        except Exception as e:
            logging.error(f"DVC operation failed: {e}")
            raise MyException(e, sys)

    def initiate_data_ingestion(self) -> DataIngestionArtifact:
        logging.info("Starting data ingestion")
        try:
            self.export_data_into_feature_store()
            self.track_dataset_with_dvc()
            artifact = DataIngestionArtifact(
                ingested_data_path=self.data_ingestion_config.data_file_path
            )
            logging.info("Data ingestion completed")
            return artifact
        except Exception as e:
            raise MyException(e, sys)


# Kubeflow Component Wrapper
@component(
    base_image="python:3.10",
    packages_to_install=[
        "pandas",
        "pymongo",
        "pyarrow",
        "dvc[s3]"
    ]
)
def data_ingestion_component() -> str:
    """
    Kubeflow pipeline component for data ingestion
    """
    ingestion = DataIngestion()
    artifact = ingestion.initiate_data_ingestion()
    return artifact.ingested_data_path