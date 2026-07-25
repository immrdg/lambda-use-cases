import os
import json
import logging
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_owner_tag(cloudtrail_client, instance_id, default_owner="DevOpsTeam"):
    """
    Queries CloudTrail for the RunInstances event to extract the launching IAM user/role.
    Handles SSO / AssumedRole names (e.g. AROA...:Gireesh -> Gireesh).
    """
    if not cloudtrail_client:
        return default_owner

    try:
        response = cloudtrail_client.lookup_events(
            LookupAttributes=[{"AttributeKey": "ResourceName", "AttributeValue": instance_id}],
            MaxResults=5,
        )
        logger.info(f"CloudTrail response: {json.dumps(response)}")
        for event in response.get("Events", []):
            if event.get("EventName") == "RunInstances":
                username = event.get("Username")

                # Fallback to CloudTrailEvent payload if Username top-level field is empty
                if not username and event.get("CloudTrailEvent"):
                    try:
                        ct_json = json.loads(event["CloudTrailEvent"])
                        user_id = ct_json.get("userIdentity", {})
                        username = user_id.get("userName") or user_id.get("principalId") or user_id.get("arn")
                    except json.JSONDecodeError:
                        pass

                if username:
                    # Parse clean username from SSO / AssumedRole format (e.g. AROA...:Gireesh -> Gireesh)
                    clean_user = username.split(":")[-1].split("/")[-1]
                    logger.info(f"Extracted owner '{clean_user}' from CloudTrail")
                    return clean_user

    except Exception as e:
        logger.warning(f"CloudTrail lookup failed: {e}")

    return default_owner


def lambda_handler(event, context):
    """
    Lambda function triggered by EventBridge when an EC2 instance enters 'running' state.
    Tags instance with LaunchDate=<current date>, Owner=<IAM User>, Environment=<env>.
    """
    logger.info(f"Received EventBridge event: {json.dumps(event)}")

    # Extract instance ID from EventBridge event payload
    detail = event.get("detail", {})
    instance_id = detail.get("instance-id") or event.get("instance_id")

    if not instance_id:
        msg = "Error: Could not extract instance-id from event payload."
        logger.error(msg)
        return {"statusCode": 400, "body": msg}

    default_owner = os.environ.get("DEFAULT_OWNER", "DevOpsTeam")
    env_name = os.environ.get("ENVIRONMENT", "dev")
    launch_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Bonus: Extract launching IAM user from CloudTrail
    try:
        ct_client = boto3.client("cloudtrail")
        owner = get_owner_tag(ct_client, instance_id, default_owner)
    except Exception:
        owner = default_owner

    tags = [
        {"Key": "LaunchDate", "Value": launch_date},
        {"Key": "Owner", "Value": owner},
        {"Key": "Environment", "Value": env_name},
    ]

    ec2 = boto3.client("ec2")
    try:
        ec2.create_tags(Resources=[instance_id], Tags=tags)
        confirmation = f"Successfully tagged EC2 instance {instance_id}: LaunchDate={launch_date}, Owner={owner}, Environment={env_name}"
        logger.info(confirmation)
        print(confirmation)

        return {
            "statusCode": 200,
            "body": {
                "message": confirmation,
                "instance_id": instance_id,
                "tags": {t["Key"]: t["Value"] for t in tags},
            },
        }

    except ClientError as e:
        logger.error(f"Failed to tag instance {instance_id}: {e}")
        raise e
