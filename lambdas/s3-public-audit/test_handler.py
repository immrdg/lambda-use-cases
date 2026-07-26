import unittest
from unittest.mock import MagicMock, patch
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
        def __init__(self, error_response=None, operation_name=None):
            super().__init__(error_response, operation_name)
            self.response = error_response
    mock_botocore.exceptions.ClientError = ClientError
    sys.modules['boto3'] = mock_boto3
    sys.modules['botocore'] = mock_botocore
    sys.modules['botocore.exceptions'] = mock_botocore.exceptions

handler_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "handler.py")
spec = importlib.util.spec_from_file_location("s3_public_audit_handler", handler_path)
handler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handler)


class TestS3PublicAuditLambda(unittest.TestCase):

    @patch.dict(os.environ, {"SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789012:s3-audit-alerts"})
    @patch.object(handler.boto3, "client")
    def test_lambda_handler_all_secure_buckets(self, mock_boto_client):
        mock_s3 = MagicMock()
        mock_sns = MagicMock()

        def client_side_effect(service_name, *args, **kwargs):
            if service_name == "s3":
                return mock_s3
            if service_name == "sns":
                return mock_sns
            return MagicMock()

        mock_boto_client.side_effect = client_side_effect

        mock_s3.list_buckets.return_value = {
            "Buckets": [{"Name": "secure-bucket-1"}, {"Name": "secure-bucket-2"}]
        }

        mock_s3.get_public_access_block.return_value = {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            }
        }
        mock_s3.get_bucket_policy_status.return_value = {"PolicyStatus": {"IsPublic": False}}
        mock_s3.get_bucket_acl.return_value = {"Grants": []}

        response = handler.lambda_handler({}, None)

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"]["total_audited"], 2)
        self.assertEqual(response["body"]["public_count"], 0)
        self.assertEqual(len(response["body"]["public_buckets"]), 0)

        mock_sns.publish.assert_not_called()

    @patch.dict(os.environ, {"SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789012:s3-audit-alerts"})
    @patch.object(handler.boto3, "client")
    def test_lambda_handler_detects_public_bucket_and_publishes_sns(self, mock_boto_client):
        mock_s3 = MagicMock()
        mock_sns = MagicMock()

        def client_side_effect(service_name, *args, **kwargs):
            if service_name == "s3":
                return mock_s3
            if service_name == "sns":
                return mock_sns
            return MagicMock()

        mock_boto_client.side_effect = client_side_effect

        mock_s3.list_buckets.return_value = {
            "Buckets": [{"Name": "secure-bucket"}, {"Name": "public-bucket"}]
        }

        def get_bpa_side_effect(Bucket):
            if Bucket == "secure-bucket":
                return {
                    "PublicAccessBlockConfiguration": {
                        "BlockPublicAcls": True,
                        "IgnorePublicAcls": True,
                        "BlockPublicPolicy": True,
                        "RestrictPublicBuckets": True,
                    }
                }
            raise handler.ClientError(
                {"Error": {"Code": "NoSuchPublicAccessBlockConfiguration", "Message": "No BPA"}},
                "GetPublicAccessBlock"
            )

        def get_policy_status_side_effect(Bucket):
            if Bucket == "public-bucket":
                return {"PolicyStatus": {"IsPublic": True}}
            return {"PolicyStatus": {"IsPublic": False}}

        def get_acl_side_effect(Bucket):
            if Bucket == "public-bucket":
                return {
                    "Grants": [
                        {
                            "Grantee": {
                                "Type": "Group",
                                "URI": "http://acs.amazonaws.com/groups/global/AllUsers"
                            },
                            "Permission": "READ"
                        }
                    ]
                }
            return {"Grants": []}

        mock_s3.get_public_access_block.side_effect = get_bpa_side_effect
        mock_s3.get_bucket_policy_status.side_effect = get_policy_status_side_effect
        mock_s3.get_bucket_acl.side_effect = get_acl_side_effect
        mock_sns.publish.return_value = {"MessageId": "msg-12345"}

        response = handler.lambda_handler({}, None)

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"]["total_audited"], 2)
        self.assertEqual(response["body"]["public_count"], 1)
        self.assertEqual(response["body"]["public_buckets"][0]["bucket_name"], "public-bucket")

        mock_sns.publish.assert_called_once()
        call_kwargs = mock_sns.publish.call_args[1]
        self.assertEqual(call_kwargs["TopicArn"], "arn:aws:sns:us-east-1:123456789012:s3-audit-alerts")
        self.assertIn("public-bucket", call_kwargs["Message"])

    @patch.object(handler.boto3, "client")
    def test_lambda_handler_list_buckets_error(self, mock_boto_client):
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.list_buckets.side_effect = handler.ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "ListBuckets"
        )

        response = handler.lambda_handler({}, None)

        self.assertEqual(response["statusCode"], 500)
        self.assertIn("Failed to list S3 buckets", response["body"])


if __name__ == "__main__":
    unittest.main()
