provider "aws" {
  region = var.region
}

locals {
  ui_index_path = "${path.module}/../ui/index.html"

  # Sample seed files (creates "folders" by prefixes)
  seed_files = {
    "csv/employee_data.csv" = "${path.module}/userdata/csv/employee_data.csv"
    "json/sample.json"      = "${path.module}/userdata/json/sample.json"
    "xml/sample.xml"        = "${path.module}/userdata/xml/sample.xml"
    "html/sample.html"      = "${path.module}/userdata/html/sample.html"
  }

  content_types = {
    "csv"  = "text/csv"
    "json" = "application/json"
    "xml"  = "application/xml"
    "html" = "text/html"
  }
}

# -------------------------
# S3 Static Website Bucket
# -------------------------
resource "aws_s3_bucket" "ui" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket_website_configuration" "ui" {
  bucket = aws_s3_bucket.ui.id

  index_document {
    suffix = "index.html"
  }
}

resource "aws_s3_bucket_public_access_block" "ui" {
  bucket = aws_s3_bucket.ui.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

data "aws_iam_policy_document" "ui_public_read" {
  statement {
    sid     = "PublicReadGetObject"
    effect  = "Allow"
    actions = ["s3:GetObject"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    resources = ["${aws_s3_bucket.ui.arn}/*"]
  }
}

resource "aws_s3_bucket_policy" "ui" {
  bucket = aws_s3_bucket.ui.id
  policy = data.aws_iam_policy_document.ui_public_read.json

  depends_on = [aws_s3_bucket_public_access_block.ui]
}

# Upload UI index.html
resource "aws_s3_object" "index" {
  bucket       = aws_s3_bucket.ui.id
  key          = "index.html"
  source       = local.ui_index_path
  content_type = "text/html"
  etag         = filemd5(local.ui_index_path)

  depends_on = [aws_s3_bucket_policy.ui]
}

# Upload seed data (creates prefixes)
resource "aws_s3_object" "seed" {
  for_each = local.seed_files

  bucket = aws_s3_bucket.ui.id
  key    = each.key
  source = each.value

  content_type = lookup(local.content_types, split(".", each.key)[length(split(".", each.key)) - 1], "text/plain")
  etag         = filemd5(each.value)

  depends_on = [aws_s3_bucket_policy.ui]
}

# -------------------------
# Lambda IAM Role
# -------------------------
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_role" {
  name               = "${var.project_name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "lambda_policy" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:aws:logs:${var.region}:*:log-group:/aws/lambda/*"]
  }

  statement {
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.ui.arn]
  }

  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.ui.arn}/*"]
  }
}

resource "aws_iam_policy" "lambda_policy" {
  name   = "${var.project_name}-lambda-policy"
  policy = data.aws_iam_policy_document.lambda_policy.json
}

resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# -------------------------
# Package Lambda
# -------------------------
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda"
  output_path = "${path.module}/build/lambda.zip"
}

resource "aws_lambda_function" "scan" {
  function_name = "${var.project_name}-scan"
  role          = aws_iam_role.lambda_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      S3_BUCKET_NAME = aws_s3_bucket.ui.bucket
      REGION     = var.region
    }
  }

  depends_on = [aws_iam_role_policy_attachment.lambda_attach]
}

# -------------------------
# API Gateway REST API
# -------------------------
resource "aws_api_gateway_rest_api" "api" {
  name = "${var.project_name}-api"
}

resource "aws_api_gateway_resource" "scan" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "scan"
}

# POST /scan
resource "aws_api_gateway_method" "post_scan" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.scan.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "post_scan" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.scan.id
  http_method             = aws_api_gateway_method.post_scan.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.scan.invoke_arn
}

# CORS: OPTIONS /scan
resource "aws_api_gateway_method" "options_scan" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.scan.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_scan" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.scan.id
  http_method = aws_api_gateway_method.options_scan.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_200" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.scan.id
  http_method = aws_api_gateway_method.options_scan.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_200" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.scan.id
  http_method = aws_api_gateway_method.options_scan.http_method
  status_code = aws_api_gateway_method_response.options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'content-type'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# Deployment + Stage
resource "aws_api_gateway_deployment" "deploy" {
  rest_api_id = aws_api_gateway_rest_api.api.id

  # ensures redeploy when integrations change
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_integration.post_scan.id,
      aws_api_gateway_integration.options_scan.id,
      aws_api_gateway_method.post_scan.id,
      aws_api_gateway_method.options_scan.id
    ]))
  }

  depends_on = [
    aws_api_gateway_integration.post_scan,
    aws_api_gateway_integration.options_scan,
    aws_api_gateway_integration_response.options_200
  ]
}

resource "aws_api_gateway_stage" "prod" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  deployment_id = aws_api_gateway_deployment.deploy.id
  stage_name    = "prod"
}

# Allow API Gateway to invoke Lambda
resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scan.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}
