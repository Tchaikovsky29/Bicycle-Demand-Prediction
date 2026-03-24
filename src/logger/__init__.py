import logging
import os
import boto3
from logging.handlers import RotatingFileHandler
from datetime import datetime
from src.constants import BUCKET_NAME
from io import StringIO


# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
LOG_DIR = "/tmp/logs"  # /tmp is writable in any container
LOG_FILE = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"
LOG_FILE_PATH = os.path.join(LOG_DIR, LOG_FILE)
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 2
FORMATTER = logging.Formatter("[ %(asctime)s ] %(name)s - %(levelname)s - %(message)s")


# ─────────────────────────────────────────────
# S3 Handler
# ─────────────────────────────────────────────
class S3LogHandler(logging.Handler):
    """
    Buffers log records in memory and flushes them to S3 on close.
    The log file is uploaded to s3://<bucket>/logs/<log_file> when
    the handler is flushed — i.e. at the end of the component run.
    """

    def __init__(self):
        super().__init__()
        self.buffer = StringIO()
        self.s3_client = boto3.client(
            "s3",
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
            endpoint_url=os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
        )
        self.bucket = BUCKET_NAME
        self.s3_key = f"logs/{LOG_FILE}"

    def emit(self, record):
        msg = self.format(record)
        self.buffer.write(msg + "\n")

    def flush_to_s3(self):
        if not self.bucket:
            return
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=self.s3_key,
                Body=self.buffer.getvalue().encode("utf-8"),
            )
        except Exception as e:
            # Don't let logging errors crash the component
            print(f"[Logger] Failed to upload logs to S3: {e}")

    def close(self):
        self.flush_to_s3()
        self.buffer.close()
        super().close()


# ─────────────────────────────────────────────
# Configure Logger
# ─────────────────────────────────────────────
def configure_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Rotating file handler — writes to /tmp/logs/ inside the container
    os.makedirs(LOG_DIR, exist_ok=True)
    file_handler = RotatingFileHandler(LOG_FILE_PATH, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT)
    file_handler.setFormatter(FORMATTER)
    file_handler.setLevel(logging.DEBUG)

    # Console handler — captured by KFP and stored in SeaweedFS automatically
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(FORMATTER)
    console_handler.setLevel(logging.INFO)

    # S3 handler — uploads full log file to S3 at end of component run
    s3_handler = S3LogHandler()
    s3_handler.setFormatter(FORMATTER)
    s3_handler.setLevel(logging.DEBUG)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.addHandler(s3_handler)

    # Suppress noisy third party loggers
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)

configure_logger()