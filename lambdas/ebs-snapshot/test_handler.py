import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
import os
import sys
import importlib.util

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

handler_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "handler.py")
spec = importlib.util.spec_from_file_location("ebs_snapshot_handler", handler_path)
handler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handler)


class TestEBSSnapshotLambda(unittest.TestCase):

    @patch.dict(os.environ, {"VOLUME_ID": "vol-12345678", "RETENTION_DAYS": "30"})
    @patch.object(handler.boto3, "client")
    def test_lambda_handler_creates_snapshot_and_deletes_stale(self, mock_boto_client):
        mock_ec2 = MagicMock()
        mock_sts = MagicMock()

        def client_side_effect(service_name, *args, **kwargs):
            if service_name == "ec2":
                return mock_ec2
            if service_name == "sts":
                return mock_sts
            return MagicMock()

        mock_boto_client.side_effect = client_side_effect
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_ec2.create_snapshot.return_value = {"SnapshotId": "snap-new123"}

        now = datetime.now(timezone.utc)
        old_time = now - timedelta(days=35)
        new_time = now - timedelta(days=5)

        mock_paginator = MagicMock()
        mock_ec2.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Snapshots": [
                    {"SnapshotId": "snap-new123", "StartTime": now},
                    {"SnapshotId": "snap-old123", "StartTime": old_time},
                    {"SnapshotId": "snap-fresh123", "StartTime": new_time},
                ]
            }
        ]

        response = handler.lambda_handler({}, None)

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"]["created_snapshot"], "snap-new123")
        self.assertEqual(response["body"]["deleted_snapshots"], ["snap-old123"])
        self.assertEqual(response["body"]["total_deleted"], 1)

        mock_ec2.create_snapshot.assert_called_once_with(
            VolumeId="vol-12345678",
            Description="Automated backup of vol-12345678 by Lambda"
        )
        mock_ec2.delete_snapshot.assert_called_once_with(SnapshotId="snap-old123")

    @patch.dict(os.environ, {}, clear=True)
    def test_lambda_handler_missing_volume_id(self):
        response = handler.lambda_handler({}, None)
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Environment variable VOLUME_ID is not set", response["body"])

    @patch.dict(os.environ, {"VOLUME_ID": "vol-87654321", "RETENTION_DAYS": "invalid_number"})
    @patch.object(handler.boto3, "client")
    def test_lambda_handler_invalid_retention_days(self, mock_boto_client):
        mock_ec2 = MagicMock()
        mock_sts = MagicMock()

        def client_side_effect(service_name, *args, **kwargs):
            if service_name == "ec2":
                return mock_ec2
            if service_name == "sts":
                return mock_sts
            return MagicMock()

        mock_boto_client.side_effect = client_side_effect
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_ec2.create_snapshot.return_value = {"SnapshotId": "snap-fallback123"}

        mock_paginator = MagicMock()
        mock_ec2.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{"Snapshots": []}]

        response = handler.lambda_handler({}, None)

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"]["created_snapshot"], "snap-fallback123")

    @patch.dict(os.environ, {"VOLUME_ID": "vol-12345678"})
    @patch.object(handler.boto3, "client")
    def test_lambda_handler_create_snapshot_failure(self, mock_boto_client):
        mock_ec2 = MagicMock()
        mock_sts = MagicMock()

        def client_side_effect(service_name, *args, **kwargs):
            if service_name == "ec2":
                return mock_ec2
            if service_name == "sts":
                return mock_sts
            return MagicMock()

        mock_boto_client.side_effect = client_side_effect
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_ec2.create_snapshot.side_effect = ClientError(
            {"Error": {"Code": "InvalidVolume.NotFound", "Message": "Volume does not exist"}},
            "CreateSnapshot"
        )

        with self.assertRaises(ClientError):
            handler.lambda_handler({}, None)


if __name__ == "__main__":
    unittest.main()
