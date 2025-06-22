import logging
from google.cloud.storage.blob import Blob
from google.api_core import retry

logger = logging.getLogger(__name__)


@retry.Retry(predicate=retry.if_transient_error, initial=5.0, maximum=15.0, multiplier=2.0, deadline=30.0)
def upload_with_retry(blob: Blob, source_file_name: str):
    """Uploads a file to GCS with retry logic and timeout."""
    logger.info(f"Attempting GCS upload (with retry): {source_file_name} to gs://{blob.bucket.name}/{blob.name}")
    blob.upload_from_filename(source_file_name, timeout=30.0)  # 30-second timeout per attempt
    logger.info(f"GCS upload successful: {source_file_name} to gs://{blob.bucket.name}/{blob.name}")
