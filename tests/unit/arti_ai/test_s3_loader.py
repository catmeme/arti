# pylint: disable=E0633, I0021
"""Test cases for the S3BucketLoader class."""

import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from arti_ai.s3_loader import S3BucketLoader


@contextmanager
def mocked_s3_bucket_loader_environment():
    """Set up the environment for the S3BucketLoader tests."""
    with patch("boto3.client") as mock_boto3_client, patch("tempfile.TemporaryDirectory") as mock_temp_dir, patch.dict(
        "os.environ",
        {"AWS_ACCESS_KEY_ID": "fake_id", "AWS_SECRET_ACCESS_KEY": "fake_secret", "AWS_SESSION_TOKEN": "fake_token"},
    ), patch("os.makedirs") as mock_os_makedirs, patch(
        "embedchain.loaders.directory_loader.DirectoryLoader.load_data", return_value={"data": []}
    ) as mock_directory_loader_load_data:

        mock_temp_dir.return_value.__enter__.return_value = "fake_tmp_dir"
        yield mock_boto3_client, mock_temp_dir, mock_os_makedirs, mock_directory_loader_load_data


class TestS3BucketLoader(unittest.TestCase):
    """Test cases for the S3BucketLoader class."""

    def setUp(self):
        """Set up the test environment using the context manager."""
        self.mock_environment = mocked_s3_bucket_loader_environment()
        self.mock_environment_context = self.mock_environment.__enter__()
        self.loader = S3BucketLoader()

    def tearDown(self):
        """Tear down the test environment."""
        self.mock_environment.__exit__(None, None, None)

    def test_s3_bucket_loader_load_data(self):
        """Test the load_data method of S3BucketLoader."""
        mock_boto3_client, _, _, _ = self.mock_environment_context
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Contents": [{"Key": "test_file.txt"}]}]
        mock_boto3_client.return_value.get_paginator.return_value = mock_paginator
        mock_boto3_client.return_value.download_file = MagicMock()

        data = self.loader.load_data("my-test-bucket")

        self.assertIsNotNone(data.get("doc_id"))
        self.assertEqual(
            len(data.get("data", [])), 0
        )  # Expecting no data since DirectoryLoader.load_data is mocked to return an empty list
        mock_boto3_client.assert_called_once_with("s3")
        mock_paginator.paginate.assert_called_once_with(Bucket="my-test-bucket", Prefix="")

    @patch(
        "os.getenv",
        side_effect=lambda x, default="fake_value": (
            "fake_value" if x in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"] else default
        ),
    )
    @patch("logging.warning")
    def test_no_warning_with_aws_credentials(self, mock_logging_warning, _mock_getenv):
        """Test that no warning is logged when AWS credentials are provided."""
        # pylint: disable=import-outside-toplevel,W0404,W0621
        from arti_ai.s3_loader import S3BucketLoader

        # pylint: enable=import-outside-toplevel

        S3BucketLoader(config={})

        mock_logging_warning.assert_not_called()

    def test_s3_bucket_loader_handles_no_files(self):
        """Test that S3BucketLoader handles no files in the bucket."""
        mock_boto3_client, _, _, _ = self.mock_environment_context
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{}]

        mock_boto3_client.return_value.get_paginator.return_value = mock_paginator
        data = self.loader.load_data("my-test-bucket")

        self.assertEqual(len(data.get("data", [])), 0)  # Expecting no data
        self.assertIsNotNone(data.get("doc_id"))

    def test_loader_skips_directories(self):
        """Test that the S3BucketLoader correctly skips directory markers."""
        mock_boto3_client, _, _, _ = self.mock_environment_context
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Contents": [{"Key": "some_folder/"}]}]

        mock_boto3_client.return_value.get_paginator.return_value = mock_paginator
        self.loader.load_data("my-test-bucket")

        mock_boto3_client.return_value.download_file.assert_not_called()

    def test_s3_bucket_loader_processes_files_correctly(self):
        """Test that S3BucketLoader processes files correctly, including invoking DirectoryLoader."""
        mock_boto3_client, _, _, mock_directory_loader_load_data = self.mock_environment_context
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Contents": [{"Key": "test_file.txt"}]}]

        mock_boto3_client.return_value.get_paginator.return_value = mock_paginator
        mock_load_data_return_value = {"data": [{"content": "file content", "meta_data": {"url": "test_file.txt"}}]}
        mock_directory_loader_load_data.return_value = mock_load_data_return_value

        data = self.loader.load_data("my-test-bucket")

        self.assertEqual(len(data.get("data", [])), 1)
        self.assertEqual(data["data"][0]["content"], "file content")
        self.assertEqual(
            data["data"][0]["meta_data"]["url"], "https://s3.us-east-1.amazonaws.com/my-test-bucket/test_file.txt"
        )


if __name__ == "__main__":
    unittest.main()
