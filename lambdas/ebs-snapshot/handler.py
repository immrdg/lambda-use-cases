import os
import logging
from datetime import datetime, timezone, timedelta
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TAG_KEY = "CreatedBy"
TAG_VALUE = "Lambda-Backup"


def lambda_handler(event, context):
    """
    Creates an EBS snapshot of the specified volume, tags it with
    CreatedBy=Lambda-Backup, then deletes snapshots older than
    RETENTION_DAYS (default 30) that carry the same tag.
    """
    volume_id = os.environ.get("VOLUME_ID")
    retention_days_str = os.environ.get("RETENTION_DAYS", "30")

    if not volume_id:
        msg = "Environment variable VOLUME_ID is not set."
        logger.error(msg)
        return {"statusCode": 400, "body": msg}

    try:
        retention_days = float(retention_days_str)
    except ValueError:
        logger.warning(f"Invalid RETENTION_DAYS '{retention_days_str}', defaulting to 30.")
        retention_days = 30.0

    ec2 = boto3.client("ec2")
    account_id = boto3.client("sts").get_caller_identity()["Account"]

    # ── Create snapshot ────────────────────────────────────────────────────────
    try:
        snap = ec2.create_snapshot(
            VolumeId=volume_id,
            Description=f"Automated backup of {volume_id} by Lambda",
        )
        snapshot_id = snap["SnapshotId"]

        ec2.create_tags(
            Resources=[snapshot_id],
            Tags=[
                {"Key": TAG_KEY,      "Value": TAG_VALUE},
                {"Key": "VolumeId",   "Value": volume_id},
                {"Key": "CreatedAt",  "Value": datetime.now(timezone.utc).isoformat()},
            ],
        )
        logger.info(f"Created snapshot: {snapshot_id} for volume {volume_id}")
    except ClientError as e:
        logger.error(f"Failed to create snapshot: {e}")
        raise

    # ── Delete stale snapshots ─────────────────────────────────────────────────
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    deleted = []

    try:
        paginator = ec2.get_paginator("describe_snapshots")
        pages = paginator.paginate(
            OwnerIds=[account_id],
            Filters=[{"Name": f"tag:{TAG_KEY}", "Values": [TAG_VALUE]},
                     {"Name": "volume-id",       "Values": [volume_id]}],
        )

        for page in pages:
            for s in page["Snapshots"]:
                start_time = s["StartTime"]
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)

                # Never delete the snapshot we just created
                if s["SnapshotId"] == snapshot_id:
                    continue

                if start_time < cutoff:
                    ec2.delete_snapshot(SnapshotId=s["SnapshotId"])
                    deleted.append(s["SnapshotId"])
                    logger.info(f"Deleted stale snapshot: {s['SnapshotId']} (created {start_time.isoformat()})")

    except ClientError as e:
        logger.error(f"Error during cleanup: {e}")
        raise

    summary = (
        f"Snapshot created: {snapshot_id}. "
        f"Deleted {len(deleted)} stale snapshot(s): {deleted or 'none'}."
    )
    logger.info(summary)

    return {
        "statusCode": 200,
        "body": {
            "created_snapshot": snapshot_id,
            "deleted_snapshots": deleted,
            "total_deleted": len(deleted),
        },
    }
