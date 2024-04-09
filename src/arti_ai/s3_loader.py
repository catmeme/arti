"""S3BucketLoader class to load data from S3 bucket."""

import hashlib
import logging
import os
import tempfile
from typing import Optional

from embedchain.loaders.base_loader import BaseLoader  # type: ignore
from embedchain.loaders.directory_loader import DirectoryLoader  # type: ignore

logger = logging.getLogger(__name__)


class S3BucketLoader(BaseLoader):
    """S3BucketLoader class to load data from S3 bucket."""

    def __init__(self, config: Optional[dict[str, str]] = None):
        """Initialize the S3BucketLoader."""
        super().__init__()
        self.config = config or {}
        self.s3_endpoint_url = self.config.get("s3_endpoint_url", "https://s3.us-east-1.amazonaws.com")

    # pylint: disable=too-many-locals
    def load_data(self, url):
        """Load data from URL, in this case an S3 bucket and prefix."""
        query_components = url.split("/", 1)
        bucket_name = query_components[0]
        prefix = query_components[1] if len(query_components) == 2 else ""

        logger.info("Loading data from S3 bucket: %s with prefix: %s", bucket_name, prefix)

        # pylint: disable=import-outside-toplevel
        import boto3

        # pylint: enable=import-outside-toplevel
        s3_client = boto3.client("s3")

        with tempfile.TemporaryDirectory() as tmp_dir:
            paginator = s3_client.get_paginator("list_objects_v2")
            s3_key_to_local_path = {}
            for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
                for obj in page.get("Contents", []):
                    local_path = os.path.join(tmp_dir, obj["Key"])
                    if obj["Key"].endswith("/"):
                        continue  # skip directories
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    s3_client.download_file(bucket_name, obj["Key"], local_path)
                    s3_key_to_local_path[obj["Key"]] = local_path

            loader = DirectoryLoader()
            loader_data = loader.load_data(tmp_dir)

            data = []
            for item in loader_data["data"]:
                s3_key = next(
                    (key for key, value in s3_key_to_local_path.items() if value.endswith(item["meta_data"]["url"])),
                    None,
                )
                item_url = f"{self.s3_endpoint_url}/{bucket_name}/{s3_key}" if s3_key else ""

                data.append(
                    {
                        "content": item["content"],
                        "meta_data": {
                            **item["meta_data"],
                            "s3_bucket_name": bucket_name,
                            "source": item_url,
                            "url": item_url,
                        },
                    }
                )

            data_content = [content["content"] for content in data]
            doc_id = hashlib.sha256((str(data_content) + url).encode()).hexdigest()

            return {
                "doc_id": doc_id,
                "data": data,
            }
