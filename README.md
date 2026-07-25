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
│   │   ├── eventbridge/          # EventBridge schedule rule
│   │   └── project/              # Orchestration (for_each over lambdas map)
│   └── env/
│       ├── dev/terragrunt.hcl
│       └── prod/terragrunt.hcl
├── lambdas/
│   └── s3-cleanup/
│       ├── handler.py
│       ├── test_handler.py
│       ├── requirements.txt
│       └── lambda-function.zip   # Built by CI, consumed by Terraform
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

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `BUCKET_NAME` | Target S3 bucket name | required |
| `RETENTION_DAYS` | Age threshold in days (supports decimals for testing) | `30` |

### IAM Policy (Least Privilege)

```json
{
  "Statement": [
    { "Action": ["s3:ListBucket"],   "Resource": "arn:aws:s3:::BUCKET" },
    { "Action": ["s3:DeleteObject"], "Resource": "arn:aws:s3:::BUCKET/*" }
  ]
}
```

### EventBridge Schedule

| Environment | Schedule |
|---|---|
| dev | `rate(1 day)` |
| prod | `cron(0 2 * * ? *)` — 2 AM UTC daily |

### Manual Invocation

```bash
aws lambda invoke \
  --function-name s3-cleanup-dev \
  --profile immrdg21 \
  --region us-east-1 \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  response.json && cat response.json
```

### End-to-End Demo (Testing with a short retention window)

To verify deletions without waiting 30 days, temporarily lower `RETENTION_DAYS` to a fraction of a day:

```bash
# Set retention to ~3 minutes
aws lambda update-function-configuration \
  --function-name s3-cleanup-dev \
  --profile immrdg21 --region us-east-1 \
  --environment "Variables={BUCKET_NAME=s3-cleanup-bucket-dev-use-case-1,RETENTION_DAYS=0.002}"

# Upload test files
for i in $(seq 1 5); do
  echo "test $i" | aws s3 cp - s3://s3-cleanup-bucket-dev-use-case-1/test-file-$i.txt \
    --profile immrdg21 --region us-east-1
done

# Wait 3+ minutes, then invoke
aws lambda invoke \
  --function-name s3-cleanup-dev \
  --profile immrdg21 --region us-east-1 \
  --payload '{}' --cli-binary-format raw-in-base64-out \
  response.json && cat response.json

# Restore to 30 days after testing
aws lambda update-function-configuration \
  --function-name s3-cleanup-dev \
  --profile immrdg21 --region us-east-1 \
  --environment "Variables={BUCKET_NAME=s3-cleanup-bucket-dev-use-case-1,RETENTION_DAYS=30}"
```

### Screenshots

#### IAM Role
<!-- screenshot: IAM role for s3-cleanup-dev with inline policy -->
`screenshots/s3-cleanup/iam-role.png`

#### Lambda Configuration
<!-- screenshot: Lambda function config showing env vars, runtime, timeout -->
`screenshots/s3-cleanup/lambda-config.png`

#### Test Invocation Output
<!-- screenshot: Lambda test result showing deleted_keys in response -->
`screenshots/s3-cleanup/test-invocation.png`

#### CloudWatch Logs
<!-- screenshot: CloudWatch log stream showing "Marked for deletion" and summary -->
`screenshots/s3-cleanup/cloudwatch-logs.png`

#### Final Result (Empty Bucket)
<!-- screenshot: S3 console showing empty bucket after cleanup -->
`screenshots/s3-cleanup/s3-empty-bucket.png`

---

### Discussion: S3 Lifecycle Rules vs Lambda

S3 Lifecycle Rules handle age-based object expiration natively with zero code and are the right default for simple time-based cleanup. Lambda is the better choice when deletion requires **conditional logic** (e.g. only delete objects matching a naming pattern or a specific metadata tag), **cross-service coordination** (e.g. verify an object is processed in DynamoDB before removing it), or **custom post-deletion actions** such as sending a detailed Slack/SNS alert with the list of deleted keys.
