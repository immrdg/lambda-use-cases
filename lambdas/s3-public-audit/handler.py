import os
import json
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

PUBLIC_GROUPS = {
    "http://acs.amazonaws.com/groups/global/AllUsers",
    "http://acs.amazonaws.com/groups/global/AuthenticatedUsers",
}

def lambda_handler(event, context):
    logger.info(f"Received event payload: {json.dumps(event)}")

    sns_topic_arn = os.environ.get("SNS_TOPIC_ARN")
    s3_client = boto3.client("s3")

    detail = event.get("detail", {})
    event_name = detail.get("eventName", "AuditTrigger")
    bucket_name = detail.get("requestParameters", {}).get("bucketName") or event.get("bucket_name")

    if not bucket_name:
        logger.warning("No bucketName found in event payload.")
        return {"statusCode": 400, "body": "No bucketName in event"}

    reasons = []
    is_public = False

    # Check conditionally based on eventName
    if event_name in ["PutBucketPublicAccessBlock", "DeleteBucketPublicAccessBlock"]:
        try:
            bpa = s3_client.get_public_access_block(Bucket=bucket_name).get("PublicAccessBlockConfiguration", {})
            disabled = [f for f in ["BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets"] if not bpa.get(f, False)]
            if disabled:
                is_public = True
                reasons.append(f"Block Public Access disabled flags: {', '.join(disabled)}")
        except ClientError:
            is_public = True
            reasons.append("Block Public Access is NOT enabled")

    elif event_name in ["PutBucketPolicy", "DeleteBucketPolicy"]:
        try:
            if s3_client.get_bucket_policy_status(Bucket=bucket_name).get("PolicyStatus", {}).get("IsPublic", False):
                is_public = True
                reasons.append("Bucket Policy grants PUBLIC access (IsPublic=True)")
        except ClientError:
            pass

    elif event_name == "PutBucketAcl":
        try:
            for grant in s3_client.get_bucket_acl(Bucket=bucket_name).get("Grants", []):
                if grant.get("Grantee", {}).get("URI") in PUBLIC_GROUPS:
                    is_public = True
                    reasons.append(f"ACL grants public access ({grant.get('Permission')})")
        except ClientError:
            pass

    else:
        # Fallback for manual or full audits: check BPA & Policy
        try:
            bpa = s3_client.get_public_access_block(Bucket=bucket_name).get("PublicAccessBlockConfiguration", {})
            disabled = [f for f in ["BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets"] if not bpa.get(f, False)]
            if disabled:
                is_public = True
                reasons.append(f"Block Public Access disabled flags: {', '.join(disabled)}")
        except ClientError:
            is_public = True
            reasons.append("Block Public Access is NOT enabled")

    if is_public and sns_topic_arn:
        lines = [
            "🚨 AWS S3 PUBLIC ACCESS ALERT 🚨",
            f"Event: {event_name}",
            f"Target Bucket: {bucket_name}\n",
            "Security Findings:",
        ]
        for r in reasons:
            lines.append(f"  - {r}")

        lines.append("\nAction Required: Re-enable Block Public Access and restrict bucket permissions.")

        try:
            boto3.client("sns").publish(
                TopicArn=sns_topic_arn,
                Subject=f"SECURITY ALERT: Public S3 Bucket ({bucket_name})",
                Message="\n".join(lines),
            )
            logger.info("SNS security alert published successfully.")
        except ClientError as e:
            logger.error(f"Error publishing SNS alert: {e}")

    return {
        "statusCode": 200,
        "body": {
            "bucket_name": bucket_name,
            "event_name": event_name,
            "is_public": is_public,
            "reasons": reasons,
        },
    }
