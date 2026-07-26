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
│   │   └── requirements.txt
│   └── auto-tagging-ec2/
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
  - `AutoTaggedBy`: `Lambda-AutoTagging`
- Prints and logs confirmation output to CloudWatch

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DEFAULT_OWNER` | Fallback owner tag if CloudTrail lookup returns no match | `DevOpsTeam` |
| `ENVIRONMENT` | Target deployment environment name | `dev` |

### IAM Policy (Least Privilege)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EC2AutoTaggingAccess",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateTags",
        "ec2:DescribeInstances"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudTrailLookupAccess",
      "Effect": "Allow",
      "Action": [
        "cloudtrail:LookupEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

### EventBridge Pattern Rule

Matches EC2 instance state-change notifications:

```json
{
  "source": ["aws.ec2"],
  "detail-type": ["EC2 Instance State-change Notification"],
  "detail": {
    "state": ["running"]
  }
}
```

### Testing & Verification

1. Launch a new t3.micro EC2 instance in us-east-1.
2. Observe EventBridge trigger the `auto-tagging-ec2-dev` Lambda function when state transitions to `running`.
3. Check instance tags in AWS EC2 Console: confirm `LaunchDate`, `Owner`, `Environment`, and `AutoTaggedBy` appear.
4. Run automated test suite:
   ```bash
   make test
   ```
