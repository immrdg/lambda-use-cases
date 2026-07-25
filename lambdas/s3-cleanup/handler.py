import os
import logging
from datetime import datetime, timezone, timedelta
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    AWS Lambda handler to clean up stale objects in a specified S3 bucket.
    Objects older than RETENTION_DAYS (default: 30) will be deleted.
    """
    bucket_name = os.environ.get("BUCKET_NAME")
    retention_days_str = os.environ.get("RETENTION_DAYS", "1")

    if not bucket_name:
        error_msg = "Environment variable BUCKET_NAME is not set."
        logger.error(error_msg)
        return {
            "statusCode": 400,
            "body": error_msg
        }

    try:
        retention_days = float(retention_days_str)
    except ValueError:
        logger.warning(f"Invalid RETENTION_DAYS value '{retention_days_str}'. Defaulting to 30 days.")
        retention_days = 30.0

    now = datetime.now(timezone.utc)
    cutoff_time = now - timedelta(days=retention_days)

    logger.info(f"Starting S3 cleanup for bucket '{bucket_name}'.")
    logger.info(f"Current UTC time: {now.isoformat()}")
    logger.info(f"Retention threshold: {retention_days} days (Objects older than {cutoff_time.isoformat()} will be deleted).")

    s3_client = boto3.client("s3")
    paginator = s3_client.get_paginator("list_objects_v2")

    total_scanned = 0
    total_deleted = 0
    deleted_objects_keys = []

    try:
        page_iterator = paginator.paginate(Bucket=bucket_name)
        objects_to_delete = []

        for page in page_iterator:
            contents = page.get("Contents", [])
            total_scanned += len(contents)

            for obj in contents:
                key = obj["Key"]
                last_modified = obj["LastModified"]

                if last_modified.tzinfo is None:
                    last_modified = last_modified.replace(tzinfo=timezone.utc)

                if last_modified < cutoff_time:
                    logger.info(f"Marked for deletion: Key='{key}', LastModified='{last_modified.isoformat()}'")
                    objects_to_delete.append({"Key": key})
                    deleted_objects_keys.append(key)

                    if len(objects_to_delete) == 1000:
                        _delete_batch(s3_client, bucket_name, objects_to_delete)
                        total_deleted += len(objects_to_delete)
                        objects_to_delete = []

        if objects_to_delete:
            _delete_batch(s3_client, bucket_name, objects_to_delete)
            total_deleted += len(objects_to_delete)

    except ClientError as e:
        logger.error(f"Error accessing S3 bucket '{bucket_name}': {str(e)}")
        raise e

    summary_msg = f"Cleanup complete. Scanned {total_scanned} objects, deleted {total_deleted} stale objects."
    logger.info(summary_msg)

    return {
        "statusCode": 200,
        "body": {
            "message": summary_msg,
            "bucket": bucket_name,
            "total_scanned": total_scanned,
            "total_deleted": total_deleted,
            "deleted_keys": deleted_objects_keys
        }
    }


def _delete_batch(s3_client, bucket_name, objects_to_delete):
    """Helper method to issue batch delete requests to S3."""
    response = s3_client.delete_objects(
        Bucket=bucket_name,
        Delete={"Objects": objects_to_delete, "Quiet": True}
    )
    errors = response.get("Errors", [])
    if errors:
        for err in errors:
            logger.error(f"Failed to delete {err.get('Key')}: {err.get('Message')}")
