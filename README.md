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
├── scripts/
│   └── live_test.sh              # End-to-end demo script
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

### End-to-End Demo

```bash
chmod +x scripts/live_test.sh
./scripts/live_test.sh
```

The script:
1. Uploads 5 test files to the bucket
2. Sets `RETENTION_DAYS=0.002` (~3 min threshold)
3. Sets EventBridge to `rate(2 minutes)`
4. Tails CloudWatch logs for 4 minutes
5. Shows final (empty) bucket state
6. Restores original config on exit

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

S3 Lifecycle Rules handle basic age-based expiration natively with zero code. Use Lambda when you need:

1. **Conditional logic** — filter by metadata tags, naming patterns, or file size before deleting
2. **Cross-service actions** — check DynamoDB before deletion, trigger SQS/SNS after
3. **Custom notifications** — send Slack/email alerts with a list of deleted keys per run
