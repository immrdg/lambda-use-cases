# AWS Lambda Automation — HeroVired Assignment

Python 3.12 Lambda functions, modular Terraform/Terragrunt infrastructure, and a GitHub Actions CI/CD pipeline for automated AWS resource management.

---

## Repository Structure

```
lambda-use-cases/
├── .github/workflows/
│   └── lambda-ci-cd.yml          # CI: detect changed lambdas, zip, commit back on PR
├── Infrastructure/
│   ├── app/                      # Terraform root module
│   ├── modules/
│   │   ├── lambda/               # Lambda + IAM least-privilege
│   │   ├── s3/                   # S3 bucket
│   │   ├── ebs/                  # EBS volume
│   │   ├── eventbridge/          # EventBridge schedule & pattern rules
│   │   ├── sns/                  # SNS Topic & Email Subscription
│   │   └── project/              # Orchestration module
│   └── env/
│       ├── dev/terragrunt.hcl
│       └── prod/terragrunt.hcl
├── lambdas/
│   ├── s3-cleanup/
│   │   ├── handler.py
│   │   ├── test_handler.py
│   │   └── requirements.txt
│   ├── ebs-snapshot/
│   │   ├── handler.py
│   │   ├── test_handler.py
│   │   └── requirements.txt
│   ├── auto-tagging-ec2/
│   │   ├── handler.py
│   │   ├── test_handler.py
│   │   └── requirements.txt
│   └── s3-public-audit/
│       ├── handler.py
│       ├── test_handler.py
│       └── requirements.txt
├── Makefile
└── terragrunt.hcl
```

---

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/lambda-ci-cd.yml`) runs on every PR to `main`/`master`:

1. **Detect** — diffs `event.before..event.after` to find which `lambdas/` subdirs changed
2. **Build** — zips only `*.py` files (excluding `test_*.py`) into `lambdas/<name>/lambda-function.zip`
3. **Commit** — pushes the zip back to the PR branch
4. **Artifact** — uploads zips as a GitHub Actions artifact (7-day retention)

Terraform reads the pre-built zip directly via `filebase64sha256` — no re-zipping at deploy time.

---

## Infrastructure Commands

```bash
# Verify credentials
aws sts get-caller-identity --profile immrdg21

# Dev environment
make init-dev
make plan-dev
make apply-dev

# Prod environment
make init-prod
make plan-prod
make apply-prod

# Tests
make test
```

---

## Assignment 1 — Automated S3 Bucket Cleanup

**Objective:** Delete objects older than 30 days from an S3 bucket on a schedule.

### How It Works

`lambdas/s3-cleanup/handler.py`:
- Reads `BUCKET_NAME` and `RETENTION_DAYS` from environment variables
- Paginates through all objects using `list_objects_v2` paginator
- Compares each object's `LastModified` (timezone-aware UTC) against `now - timedelta(days=RETENTION_DAYS)`
- Deletes stale objects in batches of 1,000 via `delete_objects`
- Logs every deleted key and a final summary to CloudWatch

---

## Assignment 3 — Auto-Tagging EC2 Instances on Launch

**Objective:** Automatically tag newly launched EC2 instances for resource tracking, ownership, and cost allocation.

### How It Works

`lambdas/auto-tagging-ec2/handler.py`:
- Listens to EventBridge rule matching `EC2 Instance State-change Notification` for `state: running`
- Extracts `instance-id` from EventBridge detail payload
- Automatically attaches tags:
  - `LaunchDate`: `<YYYY-MM-DD>` (current UTC date)
  - `Owner`: IAM user extracted from CloudTrail `RunInstances` event (Bonus Feature), defaulting to `DEFAULT_OWNER` (`DevOpsTeam`)
  - `Environment`: Target deployment environment (`dev`, `prod`)
- Prints and logs confirmation output to CloudWatch

---

## Assignment 6 — Audit S3 Buckets for Public Access and Notify

**Objective:** Detect any bucket that is publicly accessible and alert via SNS.

### How It Works

`lambdas/s3-public-audit/handler.py`:
- Audits all S3 buckets across 3 security layers:
  1. **Block Public Access Configuration**: `get_public_access_block` (checks `BlockPublicAcls`, `IgnorePublicAcls`, `BlockPublicPolicy`, `RestrictPublicBuckets`)
  2. **Bucket Policy Status**: `get_bucket_policy_status` (`IsPublic` flag)
  3. **Bucket ACL Grants**: `get_bucket_acl` (checks grants to `AllUsers` or `AuthenticatedUsers`)
- If any public or unblocked buckets are detected, formats a detailed security alert and publishes to SNS (`SNS_TOPIC_ARN`)
- Triggered on a daily schedule via EventBridge (`rate(1 day)`)

### IAM Policy (Least Privilege)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3PublicAuditAccess",
      "Effect": "Allow",
      "Action": [
        "s3:ListAllMyBuckets",
        "s3:GetBucketPublicAccessBlock",
        "s3:GetBucketPolicyStatus",
        "s3:GetBucketAcl"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SNSPublishAlertAccess",
      "Effect": "Allow",
      "Action": ["sns:Publish"],
      "Resource": "arn:aws:sns:*:*:s3-public-audit-*"
    }
  ]
}
```

### Testing & Verification

1. Deliberately disable Block Public Access or attach a public read policy on a test bucket.
2. Manually invoke or wait for the daily EventBridge trigger for `s3-public-audit-dev`.
3. Confirm SNS alert email is delivered detailing the non-compliant bucket and exact exposure reasons.
4. Re-enable Block Public Access on the test bucket immediately after testing.
