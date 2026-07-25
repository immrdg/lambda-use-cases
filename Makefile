# Makefile for running Terragrunt and tests from project root

AWS_PROFILE ?= immrdg21

.PHONY: help test init-dev plan-dev apply-dev destroy-dev init-prod plan-prod apply-prod destroy-prod

help:
	@echo "Available commands:"
	@echo "  make test          - Run Python Lambda unit tests"
	@echo "  make init-dev      - Run terragrunt init for DEV environment"
	@echo "  make plan-dev      - Run terragrunt plan for DEV environment"
	@echo "  make apply-dev     - Run terragrunt apply for DEV environment"
	@echo "  make destroy-dev   - Destroy DEV environment"
	@echo "  make init-prod     - Run terragrunt init for PROD environment"
	@echo "  make plan-prod     - Run terragrunt plan for PROD environment"
	@echo "  make apply-prod    - Run terragrunt apply for PROD environment"

test:
	python3 -m pytest lambdas/s3-cleanup/test_handler.py -v

init-dev:
	AWS_PROFILE=$(AWS_PROFILE) terragrunt --working-dir Infrastructure/env/dev init

plan-dev:
	AWS_PROFILE=$(AWS_PROFILE) terragrunt --working-dir Infrastructure/env/dev plan

apply-dev:
	AWS_PROFILE=$(AWS_PROFILE) terragrunt --working-dir Infrastructure/env/dev apply

destroy-dev:
	AWS_PROFILE=$(AWS_PROFILE) terragrunt --working-dir Infrastructure/env/dev destroy

init-prod:
	AWS_PROFILE=$(AWS_PROFILE) terragrunt --working-dir Infrastructure/env/prod init

plan-prod:
	AWS_PROFILE=$(AWS_PROFILE) terragrunt --working-dir Infrastructure/env/prod plan

apply-prod:
	AWS_PROFILE=$(AWS_PROFILE) terragrunt --working-dir Infrastructure/env/prod apply

destroy-prod:
	AWS_PROFILE=$(AWS_PROFILE) terragrunt --working-dir Infrastructure/env/prod destroy
