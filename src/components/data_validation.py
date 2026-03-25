from typing import NamedTuple
from kfp.dsl import component

@component(
    base_image = "tchaikovsky29/env-base-image:latest"
)
def data_validation_component(meta_path:str) -> NamedTuple("ValidationOutput", [
    ("validation_status", bool),
    ("message", str)
]):
    """
    Pulls the metadata for ingested dataframe and performs validation checks. 
    The validation status and message are saved to a JSON file and returned as output for downstream components.
    """
    import json
    import sys
    from collections import namedtuple
    from src.exception import MyException
    from src.logger import logging
    from src.utils.main_utils import read_yaml_file
    from src.entity.config_entity import DataValidationConfig
    from src.constants import BUCKET_NAME
    from src.configuration.aws_connection import buckets

    try:
        config = DataValidationConfig()
        bucket = buckets()
        _schema_config = read_yaml_file(file_path=config.schema_file_path)
        error_message = ""
        missing_columns = []

        logging.info("Loading metadata for ingested dataframe...")
        metadata = bucket.download_file(
            bucket = BUCKET_NAME,
            key = meta_path,
            as_object= True
        )

        metadata = json.loads(metadata.decode())
        len_check = len(_schema_config["columns"])+1 == metadata["columns"]
        if not len_check:
            error_message += f"Expected {len(_schema_config['columns'])} columns but found {metadata['columns']} columns.\n"
        else:
            logging.info(f"Column count validation passed: {metadata['columns']} columns found.")
        
        col_names = set(metadata["column_names"])

        for column in _schema_config["columns"]:
            if column not in col_names:
                missing_columns.append(column)
        
        if missing_columns:
            error_message += f"Missing columns: {', '.join(missing_columns)}.\n"
        else:
            logging.info("All required columns are present in the ingested dataframe.")
        
        if _schema_config['target_column'] not in col_names:
            error_message += f"Target column '{_schema_config['target_column']}' is missing in the ingested dataframe.\n"
        else:
            logging.info(f"Target column '{_schema_config['target_column']}' is present in the ingested dataframe.")

        validation_status = len(error_message) == 0

        ValidationOutput = namedtuple("ValidationOutput", ["validation_status", "message"])
        return ValidationOutput(validation_status, error_message.strip())
    except Exception as e:
        logging.error(f"Data validation error: {e}")
        raise MyException(e, sys)