# Example backend configuration for S3
# Rename this file to backend.tf and update with your values

terraform {
  backend "s3" {
    bucket         = "terraform-tfstate-bucket-aiuscase"
    key            = "sasi-s3-scan-poc/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}