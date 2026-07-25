import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
import os
import sys

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    mock_boto3 = MagicMock()
    mock_botocore = MagicMock()
    class ClientError(Exception):
        pass
    mock_botocore.exceptions.ClientError = ClientError
    sys.modules['boto3'] = mock_boto3
    sys.modules['botocore'] = mock_botocore
    sys.modules['botocore.exceptions'] = mock_botocore.exceptions

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import handler


class TestS3CleanupLambda(unittest.TestCase):

    @patch.dict(os.environ, {"BUCKET_NAME": "test-bucket", "RETENTION_DAYS": "30"})
    @patch("handler.boto3.client")
    def test_lambda_handler_deletes_old_objects(self, mock_boto_client):
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        now = datetime.now(timezone.utc)
        old_time = now - timedelta(days=35)
        new_time = now - timedelta(days=10)

        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "old_file.txt", "LastModified": old_time},
                    {"Key": "new_file.txt", "LastModified": new_time}
                ]
            }
        ]

        mock_s3.delete_objects.return_value = {"Quiet": True}

        response = handler.lambda_handler({}, None)

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"]["total_scanned"], 2)
        self.assertEqual(response["body"]["total_deleted"], 1)
        self.assertIn("old_file.txt", response["body"]["deleted_keys"])

        mock_s3.delete_objects.assert_called_once_with(
            Bucket="test-bucket",
            Delete={"Objects": [{"Key": "old_file.txt"}], "Quiet": True}
        )

    @patch.dict(os.environ, {}, clear=True)
    def test_lambda_handler_missing_bucket_env(self):
        response = handler.lambda_handler({}, None)
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Environment variable BUCKET_NAME is not set", response["body"])


if __name__ == "__main__":
    unittest.main()
