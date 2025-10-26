# Terraform Simplification Plan (MVP-focused)

Goal: reduce infra in `infra/main-mvp.tf` to the minimal set required for the Python ETL MVP while keeping the token-generator API.

Keep:
- S3 bucket for raw and analytics (mvp-raw/ and analytics/ prefixes)
- Lambda for ingestion (stock-pipeline-ingestion)
- EventBridge rule / schedule that triggers ingestion Lambda
- SSM parameters for storing tokens (fyers_parameter_prefix)
- SNS alerts and CloudWatch logs/metrics for the Lambda
- Token-generator API Gateway + Lambda (existing aws-token-generator)

Remove/Disable (or move to separate modules):
- RDS / databases (not used by MVP)
- Glue jobs and associated IAM policies (optional; ETL is implemented in Python and writes Parquet directly)
- ECS services and task definitions
- Athena workgroup/result bucket outputs (keep Athena docs but remove outputs tied to it)
- Extra monitoring resources referencing removed services
- Any Secrets Manager resources that are unused (use SSM SecureString instead)

IAM notes:
- Narrow Lambda role permissions: S3 (read/write to specific prefixes), SSM:GetParameter/PutParameter for token storage, SNS:Publish for alerts, CloudWatch logs.
- Remove broad permissions granting Glue/RDS/ECS unless they are explicitly needed.

Outputs:
- Only export the S3 bucket name, Lambda function name(s), token-generator API URL, and SSM parameter prefix.

Migration approach:
1. Create a branch and update TF to remove resources, adding clear commit messages.
2. Run `terraform plan` and review the resource deletions with the team before `apply`.
3. Optionally move removed resources into separate modules that are not applied by default (safer for staged rollouts).

Notes:
- This document is informational and does not change any TF files. Actual edits should be performed in a PR and include `terraform plan` output.
