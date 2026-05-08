output "website_url" {
  value = aws_s3_bucket_website_configuration.ui.website_endpoint
}

output "api_invoke_url" {
  value = "https://${aws_api_gateway_rest_api.api.id}.execute-api.${var.region}.amazonaws.com/${aws_api_gateway_stage.prod.stage_name}/scan"
}

output "bucket_name" {
  value = aws_s3_bucket.ui.bucket
}

output "lambda_name" {
  value = aws_lambda_function.scan.function_name
}