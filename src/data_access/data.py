import sys
import pandas as pd
from typing import Optional
import hashlib
from src.configuration.mongo_db_connection import MongoDBClient
from src.constants import DATABASE_NAME
from src.exception import MyException

class Data:
    """
    A class to export MongoDB records as a pandas DataFrame.
    """
    def __init__(self) -> None:
        """
        Initializes the MongoDB client connection.
        """
        try:
            self.mongo_client = MongoDBClient(database_name=DATABASE_NAME).client
        except Exception as e:
            raise MyException(e, sys)
    
    def generate_dataset_hash(self, df: pd.DataFrame) -> str:
        df = df.sort_index(axis=1).sort_values(by=list(df.columns))
        data_bytes = df.to_csv(index=False).encode()
        return hashlib.sha256(data_bytes).hexdigest()

    def export_collection_as_dataframe(self, collection_name: str, database_name: Optional[str] = None) -> pd.DataFrame:
        """
        Exports an entire MongoDB collection as a pandas DataFrame.

        Parameters:
        ----------
        collection_name : str
            The name of the MongoDB collection to export.
        database_name : Optional[str]
            Name of the database (optional). Defaults to DATABASE_NAME.

        Returns:
        -------
        pd.DataFrame
            DataFrame containing the collection data, with '_id' column removed.
        """
        try:
            # Access specified collection from the default or specified database
            if database_name is None:
                collection = self.mongo_client.database[collection_name]
            else:
                collection = self.mongo_client[database_name][collection_name]

            # Convert collection data to DataFrame
            print("Fetching data from mongoDB")
            df = pd.DataFrame(list(collection.find()))
            print(f"Data fecthed with len: {len(df)}")
            if "_id" in df.columns.to_list():
                df = df.drop(columns=["_id"], axis=1)
            hash_value = self.generate_dataset_hash(df)
            return df, hash_value

        except Exception as e:
            raise MyException(e, sys)