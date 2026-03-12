import boto3
from botocore.exceptions import ClientError
import os

class buckets():
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
            endpoint_url=os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test")
        )

    def create_bucket(self, bucket):
        try:
            self.s3_client.create_bucket(Bucket=bucket)
            print(f"Bucket '{bucket}' created")
        except ClientError as e:
            print(f"Bucket creation error: {e}")
            raise

    def create_folder(self, bucket, folder_key):
        try:
            self.s3_client.put_object(Bucket=bucket, Key=folder_key)
            print(f"Folder '{folder_key}' created in bucket '{bucket}'")
        except ClientError as e:
            print(f"Folder creation error: {e}")
            raise

    def upload_file(self, bucket, key, **kwargs):
        try:
            file_path = kwargs.get("file_path")
            if file_path:
                with open(file_path, 'rb') as f:
                    body = f.read()
                self.s3_client.put_object(Bucket=bucket, Key=key, Body=body)
                print(f"Uploaded file '{file_path}' as '{key}'")
            else:
                body = kwargs["body"]
                self.s3_client.put_object(Bucket=bucket, Key=key, Body=body)
                print(f"Uploaded content to '{key}' in bucket '{bucket}'")
        except ClientError as e:
            print(f"Upload error: {e}")
            raise

    def list_bucket(self, bucket):
        print(f"\nContents of bucket '{bucket}':")
        response = self.s3_client.list_objects_v2(Bucket=bucket)
        for obj in response.get("Contents", []):
            print(f"  - {obj['Key']}")

    def download_file(self, bucket, key, file_path=None, as_object=False):
        try:
            if as_object:
                response = self.s3_client.get_object(Bucket=bucket, Key=key)
                content = response['Body'].read()
                print(f"Loaded object from '{key}'")
                return content
            else:
                self.s3_client.download_file(bucket, key, file_path)
                print(f"Downloaded '{key}' to '{file_path}'")
        except ClientError as e:
            print(f"Download error: {e}")
            raise
    
    def path_exists_in_s3(self, bucket_name: str, path: str) -> bool:
        """
        Check if a given path (prefix or full key) exists in the S3 bucket.
        Works with LocalStack as well.
        """
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket_name, Prefix=path)
            if response['KeyCount'] > 0:
                return True
            return False
        except ClientError as e:
            print(f"Error checking path: {e}")
            return False
