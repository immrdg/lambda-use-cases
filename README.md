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

## Technical Engineering Retrospective: Problems & Resolutions

### 1. Terraform `Invalid count argument` on Computed SNS Topic ARN
- **Problem**: In `modules/lambda/main.tf`, `count = var.custom_policy_json != null ? 1 : 0` threw an error during `terraform plan` when `custom_policy_json` referenced `module.s3_audit_sns.topic_arn`. Because `topic_arn` is computed at apply time, Terraform marked `custom_policy_json` as `(known after apply)`, making `count` un-evaluable during plan.
- **Resolution**: Decoupled `count` from the policy string by introducing an explicit `enable_custom_policy` boolean variable (`count = var.enable_custom_policy ? 1 : 0`). Setting `enable_custom_policy = true` statically resolves `count` during plan while allowing dynamic topic ARN references.

### 2. AWS CloudTrail vs Native EventBridge Events
- **Problem**: EC2 state changes (Assignment 3) triggered EventBridge immediately, but S3 API modifications (Assignment 6) did not trigger EventBridge.
- **Root Cause**: EC2 state notifications (`EC2 Instance State-change Notification`) are native AWS service events emitted directly to EventBridge without CloudTrail. S3 policy modifications (`PutBucketPolicy`, `PutBucketPublicAccessBlock`) are control-plane API calls requiring an active **AWS CloudTrail Trail** (`aws_cloudtrail`) to stream events into EventBridge.
- **Resolution**: Created CloudTrail trail `dev-management-trail` (`aws cloudtrail create-trail` & `start-logging`) to stream management API events to EventBridge.

### 3. GitHub Actions PR Diffing Bug (PR #42)
- **Problem**: On PR commits, the workflow failed to detect modified Lambdas because diffing `github.event.before` vs `github.sha` only checked consecutive commits on push.
- **Resolution**: Updated `.github/workflows/lambda-ci-cd.yml` for `pull_request` events to diff `github.event.pull_request.base.sha` vs `github.event.pull_request.head.sha`, reliably identifying every changed Lambda handler across the PR branch.

### 4. Pytest Module Namespace Collisions
- **Problem**: Standard `pytest lambdas/*/test_handler.py` cached `sys.modules['handler']` from the first test suite, causing cross-suite test import failures.
- **Resolution**: Configured dynamic module loading via `importlib.util.spec_from_file_location` in test files and updated `Makefile` to invoke pytest with `--import-mode=importlib`.

### 5. Architectural Decision: Why Event-Driven (CloudTrail) Over Scheduled Event for S3 Audit
- **Zero Security Exposure Window (Immediate Incident Response)**: Scheduled daily audits leave up to a 24-hour window where a bucket remains publicly exposed before detection. Event-driven triggers fire **immediately** upon security modification (`PutBucketPublicAccessBlock`, `PutBucketPolicy`, `PutBucketAcl`).
- **Audit Attribution & Context**: Event-driven triggers capture CloudTrail metadata detailing **who** made the change (`userIdentity`), **what** action occurred (`eventName`), and **when** it happened (`eventTime`). Scheduled audits only know *that* a bucket is public.
- **Resource & Cost Efficiency**: Eliminates unnecessary daily Lambda invocations and S3 API polling when no security configuration changes have occurred.
- **Targeted Sub-Second Execution**: Audits the single target bucket extracted from `event.detail.requestParameters.bucketName` rather than performing full account-wide `list_buckets()` iterations.

---

## Assignment Implementations

### Assignment 1 — Automated S3 Bucket Cleanup
- **Objective**: Delete objects older than 30 days from an S3 bucket on a daily schedule.
- **Handler**: `lambdas/s3-cleanup/handler.py`
- **Trigger**: EventBridge schedule (`rate(1 day)`).

### Assignment 2 — EBS Snapshot Management
- **Objective**: Create tagged EBS volume snapshots and delete snapshots older than 30 days.
- **Handler**: `lambdas/ebs-snapshot/handler.py`
- **Trigger**: EventBridge schedule (`rate(7 days)`).

### Assignment 3 — Auto-Tagging EC2 Instances on Launch
- **Objective**: Auto-tag newly launched EC2 instances (`LaunchDate`, `Environment`, `Owner`).
- **Bonus Feature**: CloudTrail `LookupEvents` extracts the launching IAM user or AWS SSO session user.
- **Handler**: `lambdas/auto-tagging-ec2/handler.py`
- **Trigger**: EventBridge rule (`EC2 Instance State-change Notification` for `state: running`).

### Assignment 6 — Audit S3 Buckets for Public Access & Notify
- **Objective**: Audit S3 buckets for public access exposure and send SNS email alerts.
- **Handler**: `lambdas/s3-public-audit/handler.py`
- **Inspection**: Audits Block Public Access, Bucket Policy `IsPublic` flag, and public ACL grants.
- **Notification**: SNS Topic (`s3-public-audit-dev-alerts`) sending email alerts to `d.gireesh21@gmail.com`.
- **Trigger**: EventBridge rule matching CloudTrail events (`PutBucketPublicAccessBlock`, `DeleteBucketPublicAccessBlock`, `PutBucketPolicy`, `DeleteBucketPolicy`, `PutBucketAcl`).

---

## Running Commands

```bash
# Verify credentials
aws sts get-caller-identity --profile immrdg21

# Dev environment deployment
make init-dev
make plan-dev
make apply-dev

# Prod environment deployment
make init-prod
make plan-prod
make apply-prod

# Unit tests
make test
```
