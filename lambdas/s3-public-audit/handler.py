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


def check_bucket_public_access(s3_client, bucket_name):
    """
    Inspects an S3 bucket across three security controls:
    1. Block Public Access (BPA) configuration
    2. Bucket Policy status (IsPublic flag)
    3. Bucket ACL grants (AllUsers / AuthenticatedUsers)

    Returns a dict with `is_public` (bool) and `reasons` (list of str).
    """
    reasons = []
    is_public = False

    # 1. Check Block Public Access Configuration
    try:
        bpa_response = s3_client.get_public_access_block(Bucket=bucket_name)
        bpa_config = bpa_response.get("PublicAccessBlockConfiguration", {})

        disabled_flags = [
            flag for flag in ["BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets"]
            if not bpa_config.get(flag, False)
        ]

        if disabled_flags:
            is_public = True
            reasons.append(f"Block Public Access is incomplete (disabled flags: {', '.join(disabled_flags)})")

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code in ["NoSuchPublicAccessBlockConfiguration", "NoSuchBucket"]:
            is_public = True
            reasons.append("Block Public Access configuration is NOT enabled")
        else:
            logger.warning(f"Could not retrieve Public Access Block for '{bucket_name}': {e}")

    # 2. Check Bucket Policy Status
    try:
        policy_status = s3_client.get_bucket_policy_status(Bucket=bucket_name)
        if policy_status.get("PolicyStatus", {}).get("IsPublic", False):
            is_public = True
            reasons.append("Bucket Policy grants PUBLIC access (IsPublic=True)")

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code not in ["NoSuchBucketPolicy", "NoSuchBucket", "AccessDenied"]:
            logger.warning(f"Could not retrieve Bucket Policy Status for '{bucket_name}': {e}")

    # 3. Check Bucket ACL Grants
    try:
        acl_response = s3_client.get_bucket_acl(Bucket=bucket_name)
        for grant in acl_response.get("Grants", []):
            grantee = grant.get("Grantee", {})
            uri = grantee.get("URI")
            if uri in PUBLIC_GROUPS:
                permission = grant.get("Permission")
                is_public = True
                reasons.append(f"ACL grants '{permission}' access to public group ({uri.split('/')[-1]})")

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code not in ["NoSuchBucket", "AccessDenied"]:
            logger.warning(f"Could not retrieve ACL for '{bucket_name}': {e}")

    return {
        "bucket_name": bucket_name,
        "is_public": is_public,
        "reasons": reasons,
    }


def lambda_handler(event, context):
    """
    Audits all S3 buckets in the AWS account for public access exposure.
    If any buckets are public or lack Block Public Access enforcement, sends an SNS alert.
    """
    logger.info("Starting S3 bucket public access security audit...")

    sns_topic_arn = os.environ.get("SNS_TOPIC_ARN")
    s3_client = boto3.client("s3")

    try:
        response = s3_client.list_buckets()
        buckets = response.get("Buckets", [])
    except ClientError as e:
        error_msg = f"Failed to list S3 buckets: {e}"
        logger.error(error_msg)
        return {"statusCode": 500, "body": error_msg}

    audited_count = len(buckets)
    public_buckets = []

    logger.info(f"Discovered {audited_count} S3 bucket(s) to audit.")

    for bucket in buckets:
        bucket_name = bucket["Name"]
        result = check_bucket_public_access(s3_client, bucket_name)
        if result["is_public"]:
            public_buckets.append(result)
            logger.warning(f"SECURITY ALERT: Bucket '{bucket_name}' is PUBLIC or unblocked. Reasons: {result['reasons']}")
        else:
            logger.info(f"Bucket '{bucket_name}' is secure (Block Public Access enforced, non-public).")

    public_count = len(public_buckets)
    summary_msg = f"Audit complete. Audited {audited_count} bucket(s). Found {public_count} public/unrestricted bucket(s)."
    logger.info(summary_msg)

    # Send SNS notification if public buckets are detected
    if public_count > 0 and sns_topic_arn:
        alert_lines = [
            "🚨 AWS S3 PUBLIC ACCESS AUDIT ALERT 🚨\n",
            f"Automated security audit detected {public_count} publicly accessible or unblocked S3 bucket(s):\n",
        ]

        for item in public_buckets:
            alert_lines.append(f"• Bucket: {item['bucket_name']}")
            for reason in item["reasons"]:
                alert_lines.append(f"  - {reason}")
            alert_lines.append("")

        alert_lines.append(f"\nTotal Audited: {audited_count} | Public Buckets: {public_count}")
        alert_lines.append("Action Required: Enable Block Public Access and review bucket policies/ACLs immediately.")

        alert_message = "\n".join(alert_lines)

        try:
            sns_client = boto3.client("sns")
            sns_response = sns_client.publish(
                TopicArn=sns_topic_arn,
                Subject=f"SECURITY ALERT: {public_count} Public S3 Bucket(s) Detected",
                Message=alert_message,
            )
            logger.info(f"Published SNS alert message (MessageId: {sns_response.get('MessageId')}) to {sns_topic_arn}")
        except ClientError as e:
            logger.error(f"Failed to publish SNS alert to {sns_topic_arn}: {e}")

    return {
        "statusCode": 200,
        "body": {
            "message": summary_msg,
            "total_audited": audited_count,
            "public_count": public_count,
            "public_buckets": public_buckets,
        },
    }
