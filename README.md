# AWS Lambda Automation Infrastructure (`MyAWSInfraProj1` Pattern)

This repository contains the multi-Lambda source code, modular Terraform infrastructure, Terragrunt environment configurations, and GitHub CI/CD pipeline modeled after the architecture in [`MyAWSInfraProj1`](https://github.com/immrdg/MyAWSInfraProj1.git).

---

## 📁 Repository Directory Structure

```text
lambda-use-cases/
├── terragrunt.hcl                               # Root terragrunt configuration
├── Makefile                                     # Convenient CLI shortcuts
├── .github/
│   └── workflows/
│       └── lambda-ci-cd.yml                     # GitHub Actions CI/CD pipeline
├── Infrastructure/
│   ├── app/                                     # Terraform root module (wrapper)
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── modules/                                 # Reusable Infrastructure Modules
│   │   ├── s3/                                  # S3 Bucket module
│   │   ├── lambda/                              # AWS Lambda + IAM least-privilege policy module
│   │   ├── eventbridge/                         # EventBridge schedule trigger module
│   │   └── project/                             # Orchestration module
│   └── env/                                     # Terragrunt Environment Configurations
│       ├── dev/
│       │   └── terragrunt.hcl                   # Dev Environment Terragrunt Config
│       └── prod/
│           └── terragrunt.hcl                   # Prod Environment Terragrunt Config
└── lambda/                                      # Python 3.12 Lambda Handlers
    └── s3_cleanup/                              # Problem 1: S3 Stale Object Cleanup
        ├── index.py                             # Lambda handler logic
        └── test_s3_cleanup.py                   # Unit tests
```

---

## 🔑 AWS Profile Configuration

All Terragrunt configurations use the AWS profile **`immrdg21`**.

Verify credentials:
```bash
aws sts get-caller-identity --profile immrdg21
```

---

## 🚀 Correct Flag Order for Terragrunt Commands

Global Terragrunt flags like `--working-dir` **must come BEFORE** the command (`init`, `plan`, `apply`):

### 1. From Project Root:
```bash
export AWS_PROFILE=immrdg21

# Init DEV environment
terragrunt --working-dir Infrastructure/env/dev init

# Plan DEV environment
terragrunt --working-dir Infrastructure/env/dev plan

# Apply DEV environment
terragrunt --working-dir Infrastructure/env/dev apply

# Plan PROD environment
terragrunt --working-dir Infrastructure/env/prod plan
```

### 2. By Navigating to Environment Directory:
```bash
export AWS_PROFILE=immrdg21

cd Infrastructure/env/dev
terragrunt init
terragrunt plan
terragrunt apply
```

### 3. Using Makefile Shortcuts:
```bash
make init-dev
make plan-dev
make apply-dev
make test
```

---

## 🐍 Problem 1: Automated S3 Bucket Cleanup Lambda

### Objective
Automate deletion of stale objects older than **30 days** in an S3 bucket using Python 3.12 & Boto3.

### Key Logic Highlights (`lambda/s3_cleanup/index.py`)
- Paginates through bucket objects using `get_paginator('list_objects_v2')`.
- Compares `LastModified` UTC timestamp against `datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)`.
- Deletes objects in batches of 1,000 via `delete_objects`.
- Parameterized via environment variables `BUCKET_NAME` and `RETENTION_DAYS`.

---

## 🔐 IAM Least-Privilege Policy

The Lambda IAM role enforces strict least-privilege inline policy permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3ListBucketAccess",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::s3-cleanup-bucket-dev-use-case-1"
    },
    {
      "Sid": "S3DeleteObjectAccess",
      "Effect": "Allow",
      "Action": ["s3:DeleteObject"],
      "Resource": "arn:aws:s3:::s3-cleanup-bucket-dev-use-case-1/*"
    }
  ]
}
```

---

## 💡 Discussion Point: Native S3 Lifecycle Rules vs. AWS Lambda

> **When would you use Lambda instead of native S3 Lifecycle Rules?**
>
> While S3 Lifecycle Rules handle basic age-based object expiration natively with zero custom code, **AWS Lambda** is required when cleanup criteria involve:
> 1. **Complex Conditional Logic**: Filtering objects based on metadata tags, specific naming regex patterns, file header content, or size thresholds.
> 2. **Cross-System Dependencies**: Querying an external database (e.g., DynamoDB/RDS) to verify if an object has been processed before deleting it.
> 3. **Custom Notifications & Auditing**: Sending immediate Slack/SNS alerts or maintaining detailed audit logs of deleted files before removal.
