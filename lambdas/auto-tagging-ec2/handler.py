import os
import json
import logging
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_launcher_iam_user(cloudtrail_client, instance_id, default_owner="DevOpsTeam"):
    """
    Queries CloudTrail events to identify the IAM user or entity that launched the EC2 instance.
    Falls back to default_owner if CloudTrail lookup produces no match or fails.
    """
    if not cloudtrail_client:
        return default_owner

    try:
        # Lookup CloudTrail events associated with the instance ID
        response = cloudtrail_client.lookup_events(
            LookupAttributes=[
                {"AttributeKey": "ResourceName", "AttributeValue": instance_id}
            ],
            MaxResults=10,
        )

        for event in response.get("Events", []):
            if event.get("EventName") == "RunInstances":
                if event.get("Username"):
                    logger.info(f"Found IAM username from CloudTrail event: {event['Username']}")
                    return event["Username"]

                # Fallback to parsing raw CloudTrailEvent JSON payload
                cloudtrail_payload = event.get("CloudTrailEvent")
                if cloudtrail_payload:
                    try:
                        ct_json = json.loads(cloudtrail_payload)
                        user_identity = ct_json.get("userIdentity", {})
                        user_name = (
                            user_identity.get("userName")
                            or user_identity.get("principalId")
                            or user_identity.get("arn")
                        )
                        if user_name:
                            logger.info(f"Parsed username '{user_name}' from CloudTrail JSON")
                            return user_name
                    except json.JSONDecodeError:
                        pass

    except ClientError as e:
        logger.warning(f"Could not query CloudTrail for instance {instance_id}: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error during CloudTrail lookup: {e}")

    logger.info(f"Defaulting Owner tag to '{default_owner}' for instance {instance_id}")
    return default_owner


def lambda_handler(event, context):
    """
    Lambda function triggered by EventBridge on EC2 Instance State-change Notification (running state).
    Automatically tags the newly launched instance with LaunchDate, Owner, and Environment.
    """
    logger.info(f"Received EventBridge event: {json.dumps(event)}")

    # Extract instance-id from various possible event structures
    detail = event.get("detail", {})
    instance_id = (
        detail.get("instance-id")
        or event.get("instance_id")
        or event.get("instance-id")
    )

    # Secondary check for CloudTrail RunInstances event structure
    if not instance_id and "responseElements" in detail:
        try:
            instances = detail["responseElements"]["instancesSet"]["items"]
            if instances:
                instance_id = instances[0].get("instanceId")
        except (KeyError, IndexError, TypeError):
            pass

    if not instance_id:
        msg = "Error: Could not extract instance-id from EventBridge event payload."
        logger.error(msg)
        return {"statusCode": 400, "body": msg}

    default_owner = os.environ.get("DEFAULT_OWNER", "DevOpsTeam")
    environment_name = os.environ.get("ENVIRONMENT", "dev")
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    ec2_client = boto3.client("ec2")

    try:
        cloudtrail_client = boto3.client("cloudtrail")
    except Exception:
        cloudtrail_client = None

    # Determine Owner tag (Bonus CloudTrail lookup)
    owner = get_launcher_iam_user(cloudtrail_client, instance_id, default_owner=default_owner)

    tags = [
        {"Key": "LaunchDate", "Value": current_date},
        {"Key": "Owner", "Value": owner},
        {"Key": "Environment", "Value": environment_name},
        {"Key": "AutoTaggedBy", "Value": "Lambda-AutoTagging"},
    ]

    try:
        ec2_client.create_tags(Resources=[instance_id], Tags=tags)
        confirmation_msg = (
            f"Successfully auto-tagged EC2 instance {instance_id} "
            f"with LaunchDate={current_date}, Owner={owner}, Environment={environment_name}."
        )
        logger.info(confirmation_msg)
        print(confirmation_msg)

        return {
            "statusCode": 200,
            "body": {
                "message": confirmation_msg,
                "instance_id": instance_id,
                "tags": {t["Key"]: t["Value"] for t in tags},
            },
        }

    except ClientError as e:
        error_msg = f"Failed to tag EC2 instance {instance_id}: {e}"
        logger.error(error_msg)
        raise e
