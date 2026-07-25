import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
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

# Import handler module dynamically from current directory to prevent sys.modules collisions
handler_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "handler.py")
spec = importlib.util.spec_from_file_location("auto_tagging_ec2_handler", handler_path)
handler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handler)


class TestAutoTaggingEC2Lambda(unittest.TestCase):

    @patch.dict(os.environ, {"DEFAULT_OWNER": "DevOpsTeam", "ENVIRONMENT": "dev"})
    @patch.object(handler.boto3, "client")
    def test_lambda_handler_success(self, mock_boto_client):
        mock_ec2 = MagicMock()
        mock_cloudtrail = MagicMock()

        def client_side_effect(service_name, *args, **kwargs):
            if service_name == "ec2":
                return mock_ec2
            if service_name == "cloudtrail":
                return mock_cloudtrail
            return MagicMock()

        mock_boto_client.side_effect = client_side_effect
        mock_cloudtrail.lookup_events.return_value = {"Events": []}

        event = {
            "version": "0",
            "id": "7bf3a259-7715-45a7-95b0-77a82b3a1a5b",
            "detail-type": "EC2 Instance State-change Notification",
            "source": "aws.ec2",
            "account": "123456789012",
            "time": "2026-07-25T23:00:00Z",
            "region": "us-east-1",
            "resources": ["arn:aws:ec2:us-east-1:123456789012:instance/i-0123456789abcdef0"],
            "detail": {
                "instance-id": "i-0123456789abcdef0",
                "state": "running"
            }
        }

        response = handler.lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"]["instance_id"], "i-0123456789abcdef0")
        self.assertEqual(response["body"]["tags"]["Owner"], "DevOpsTeam")
        self.assertEqual(response["body"]["tags"]["Environment"], "dev")
        self.assertEqual(
            response["body"]["tags"]["LaunchDate"],
            datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )

        mock_ec2.create_tags.assert_called_once_with(
            Resources=["i-0123456789abcdef0"],
            Tags=[
                {"Key": "LaunchDate", "Value": datetime.now(timezone.utc).strftime("%Y-%m-%d")},
                {"Key": "Owner", "Value": "DevOpsTeam"},
                {"Key": "Environment", "Value": "dev"},
                {"Key": "AutoTaggedBy", "Value": "Lambda-AutoTagging"}
            ]
        )

    @patch.dict(os.environ, {"DEFAULT_OWNER": "DevOpsTeam", "ENVIRONMENT": "prod"})
    @patch.object(handler.boto3, "client")
    def test_lambda_handler_cloudtrail_owner_lookup(self, mock_boto_client):
        mock_ec2 = MagicMock()
        mock_cloudtrail = MagicMock()

        def client_side_effect(service_name, *args, **kwargs):
            if service_name == "ec2":
                return mock_ec2
            if service_name == "cloudtrail":
                return mock_cloudtrail
            return MagicMock()

        mock_boto_client.side_effect = client_side_effect
        mock_cloudtrail.lookup_events.return_value = {
            "Events": [
                {
                    "EventName": "RunInstances",
                    "Username": "john.doe@example.com"
                }
            ]
        }

        event = {
            "detail": {
                "instance-id": "i-09999888777666555",
                "state": "running"
            }
        }

        response = handler.lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"]["tags"]["Owner"], "john.doe@example.com")
        self.assertEqual(response["body"]["tags"]["Environment"], "prod")

    def test_lambda_handler_missing_instance_id(self):
        event = {"detail": {"state": "running"}}
        response = handler.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Could not extract instance-id", response["body"])

    @patch.object(handler.boto3, "client")
    def test_lambda_handler_ec2_client_error(self, mock_boto_client):
        mock_ec2 = MagicMock()
        mock_boto_client.return_value = mock_ec2
        mock_ec2.create_tags.side_effect = ClientError(
            {"Error": {"Code": "InvalidInstanceID.NotFound", "Message": "Instance does not exist"}},
            "CreateTags"
        )

        event = {"detail": {"instance-id": "i-invalid123"}}

        with self.assertRaises(ClientError):
            handler.lambda_handler(event, None)


if __name__ == "__main__":
    unittest.main()
