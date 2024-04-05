"""Unit tests for the Arti AI app."""

import importlib
import unittest
from unittest.mock import MagicMock, patch


class TestArtiApp(unittest.TestCase):
    """Test the Arti AI app."""

    @patch("builtins.print")
    @patch("embedchain.App.from_config")
    @patch("embedchain.loaders.directory_loader.DirectoryLoader")
    def test_ask_ai(self, _mock_directory_loader, mock_from_config, mock_print):
        """Test the ask_ai function."""
        # pylint: disable=import-outside-toplevel
        from arti_ai.app import ask_ai

        # pylint: enable=import-outside-toplevel

        mock_app_instance = MagicMock()
        mock_app_instance.query.return_value = "Mocked response"
        mock_from_config.return_value = mock_app_instance

        question = "What is the meaning of life?"
        expected_response = "Mocked response"

        response = ask_ai(question)

        mock_print.assert_called_with(f"Processing question: {question}")
        mock_app_instance.query.assert_called_with(question)

        self.assertEqual(response, expected_response)

    @patch("os.getenv")
    def test_config_args_with_env_var(self, mock_getenv):
        """Test config_args when APP_CONFIG_FILE environment variable is set."""
        mock_getenv.return_value = "path/to/config/file"

        with patch.dict("arti_ai.app.config_args", {}):
            # pylint: disable=import-outside-toplevel
            import arti_ai.app

            # pylint: enable=import-outside-toplevel

            importlib.reload(arti_ai.app)
            self.assertEqual(arti_ai.app.config_args["config_file"], "path/to/config/file")

    @patch("os.getenv")
    def test_config_args_without_env_var(self, mock_getenv):
        """Test config_args when APP_CONFIG_FILE environment variable is not set."""
        mock_getenv.return_value = None

        with patch.dict("arti_ai.app.config_args", {}):
            # pylint: disable=import-outside-toplevel
            import arti_ai.app

            # pylint: enable=import-outside-toplevel

            importlib.reload(arti_ai.app)
            self.assertNotIn("config_file", arti_ai.app.config_args)

    @patch("os.getenv", side_effect=lambda key, default=None: default)
    @patch("embedchain.loaders.directory_loader.DirectoryLoader")
    def test_get_loader_and_asset_root_directory(self, mock_directory_loader, _mock_getenv):
        """Test get_loader and asset root as directory."""
        # pylint: disable=import-outside-toplevel
        from arti_ai.app import get_loader_and_asset_root

        # pylint: enable=import-outside-toplevel

        _, root_path = get_loader_and_asset_root()
        mock_directory_loader.assert_called_with(config={"recursive": True})
        self.assertEqual(root_path, "assets")

    @patch("os.getenv", side_effect=lambda key, default=None: "my-test-bucket" if key == "APP_BUCKET_NAME" else default)
    @patch("arti_ai.s3_loader.S3BucketLoader")
    def test_get_loader_and_asset_root_s3(self, mocker_s3_bucket_loader, _mock_getenv):
        """Test get loader and asset root as S3."""
        # pylint: disable=import-outside-toplevel
        from arti_ai.app import get_loader_and_asset_root

        # pylint: enable=import-outside-toplevel
        _, root_path = get_loader_and_asset_root()
        mocker_s3_bucket_loader.assert_called_with()
        self.assertEqual(root_path, "my-test-bucket/assets")

    @patch("arti_ai.app.get_loader_and_asset_root", return_value=(MagicMock(), "assets"))
    @patch("embedchain.App.from_config")
    def test_load_data(self, mock_app_from_config, _):
        """Test data is loaded correctly."""
        # pylint: disable=import-outside-toplevel
        from arti_ai.app import load_data

        # pylint: enable=import-outside-toplevel

        _ = load_data()
        mock_app_from_config.assert_called_once()

    @patch("arti_ai.app.config.get_embedchain_config", return_value={})
    @patch("embedchain.App.from_config")
    def test_reset_data(self, mock_from_config, _mock_get_config):
        """Test reset_data correctly resets the vector database."""
        # pylint: disable=import-outside-toplevel
        from arti_ai.app import reset_data

        # pylint: enable=import-outside-toplevel

        mock_app_instance = MagicMock()
        mock_from_config.return_value = mock_app_instance

        reset_data()

        mock_app_instance.reset.assert_called_once()


if __name__ == "__main__":
    unittest.main()
