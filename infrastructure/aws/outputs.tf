# ============================================================
# Outputs: Key values needed after deployment
# ============================================================

output "s3_bucket_name" {
  description = "S3 bucket name for PDF uploads"
  value       = aws_s3_bucket.vehicle_docs.bucket
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN (needed for Snowflake Storage Integration)"
  value       = aws_s3_bucket.vehicle_docs.arn
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.pdf_ingestor.function_name
}

output "snowflake_s3_role_arn" {
  description = "IAM Role ARN for Snowflake to assume (use in CREATE STORAGE INTEGRATION)"
  value       = aws_iam_role.snowflake_s3_access.arn
}

output "kms_key_arn" {
  description = "KMS key ARN used for encryption"
  value       = aws_kms_key.data_key.arn
}

output "dlq_url" {
  description = "Dead Letter Queue URL for monitoring failed ingestions"
  value       = aws_sqs_queue.dlq.url
}
