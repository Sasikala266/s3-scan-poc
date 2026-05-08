# S3 Scan POC (S3 Static Website + API Gateway REST + Lambda)

## What it creates
- S3 bucket with static website hosting and public index.html
- Seed folders/prefixes and sample data objects: csv/, json/, xml/, html/
- Lambda function to locate a file by name and return its S3 URI
- API Gateway REST API: POST /prod/scan (CORS enabled)

## Deploy (GitHub Actions)
1. Add secret `AWS_ROLE_TO_ASSUME` (OIDC) OR AWS access key secrets.
2. Push to main or run workflow manually.

## Outputs
- `website_url` -> open in browser
- `api_invoke_url` -> used by UI fetch

## Local Terraform (optional)
cd infra
terraform init
terraform plan
terraform apply