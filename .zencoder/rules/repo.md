---
description: Repository Information Overview
alwaysApply: true
---

# AWS Stock Price Feed Pipeline Information

## Summary
A production-ready AWS-based data pipeline for ingesting and processing stock OHLCV (Open, High, Low, Close, Volume) data from the Fyers API with automatic token management. The pipeline implements a modern data lake architecture following raw → curated data patterns with comprehensive monitoring and alerting.

## Structure
- **ingestion/**: Main ingestion scripts and Lambda functions
- **aws-token-generator/**: Token generation and management components
- **infra/**: Terraform infrastructure as code
- **deployment/**: Deployment scripts and packages
- **scripts/**: Utility scripts for setup and management
- **etl/**: ETL processing scripts for data transformation
- **sql/**: SQL schemas and queries for analytics
- **examples/**: Example code and usage patterns

## Language & Runtime
**Language**: Python 3.11
**Build System**: Terraform
**Package Manager**: pip
**Infrastructure**: AWS (Lambda, S3, EventBridge, SNS, SSM)

## Dependencies
**Main Dependencies**:
- boto3 (AWS SDK for Python)
- requests (HTTP client)
- pytz (Timezone handling)
- websocket-client (WebSocket support)
- oauthlib (OAuth implementation)

**Infrastructure Dependencies**:
- Terraform >= 1.0
- AWS CLI
- AWS services: Lambda, S3, EventBridge, SNS, SSM Parameter Store, CloudWatch

## Build & Installation
```bash
# Initialize Terraform
cd infra
terraform init

# Deploy MVP infrastructure
terraform plan -var="notification_email=your-email@example.com"
terraform apply -var="notification_email=your-email@example.com"

# Automated deployment script
./deploy.ps1 -Email "your-email@example.com" -Apply  # Windows
```

## Docker
**Dockerfile**: `ingestion/Dockerfile`
**Configuration**: Container for data ingestion with Python dependencies

## Main Components
**Ingestion Lambda**: `ingestion/lambda_ingestion.py`
- Fetches OHLCV data from Fyers API
- Handles token refresh and authentication
- Stores data in S3 with partitioning

**Token Generator**: `aws-token-generator/lambda_function.py`
- Manages API tokens and credentials
- Provides web UI for token generation
- Stores tokens in SSM Parameter Store

**ETL Processing**: `etl/lightweight_etl.py`
- Transforms raw JSON data to CSV format
- Partitions data by symbol, year, month, day
- Optimized for Athena querying

**Infrastructure**: `infra/main-mvp.tf`
- Defines AWS resources using Terraform
- Configures Lambda, S3, EventBridge, SNS
- Sets up monitoring and alerting

## Testing
**Framework**: Manual testing with AWS Lambda invocation
**Test Location**: `scripts/pre_deployment_check.py`
**Run Command**:
```bash
# Test Lambda function
aws lambda invoke --function-name stock-pipeline-ingestion --payload '{}' response.json

# Check CloudWatch logs
aws logs tail /aws/lambda/stock-pipeline-ingestion --follow
```

## Data Flow
1. EventBridge triggers Lambda function on schedule
2. Lambda checks trading hours and token validity
3. If token expired, automatic refresh from SSM Parameter Store
4. Fetch OHLCV data from Fyers API
5. Store raw JSON data in S3 with partitioning
6. ETL Lambda transforms data to CSV/Parquet format
7. Query data using Athena (production setup)

## Configuration
**API Credentials**: Stored in SSM Parameter Store
**Schedule**: EventBridge rule (every 5 minutes during trading hours)
**Data Storage**: S3 bucket with lifecycle management
**Monitoring**: CloudWatch logs and SNS notifications