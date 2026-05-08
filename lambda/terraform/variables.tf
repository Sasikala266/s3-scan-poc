variable "region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "s3-scan-poc"
}

variable "bucket_name" {
  type    = string
  default = "s3-scan-sasi-learning" # change if needed to unique
}