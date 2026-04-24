# ============================================================
# Terraform: AWS Provider & Backend Configuration
# ============================================================
# Production Standard: Remote state in S3 with DynamoDB locking
# For this project, we use local state. Uncomment the backend
# block below when deploying to a real environment.
# ============================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment for production remote state:
  # backend "s3" {
  #   bucket         = "automotive-copilot-tfstate"
  #   key            = "infra/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "terraform-lock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "automotive-copilot"
      Environment = var.environment
      ManagedBy   = "terraform"
      Owner       = var.owner_email
    }
  }
}

# ============================================================
# KMS: Encryption Key for S3 & Secrets
# ============================================================
resource "aws_kms_key" "data_key" {
  description             = "CMK for Automotive Copilot data encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = { Name = "${var.project_name}-data-key" }
}

resource "aws_kms_alias" "data_key_alias" {
  name          = "alias/${var.project_name}-data-key"
  target_key_id = aws_kms_key.data_key.key_id
}

# ============================================================
# S3: Document Landing Zone (Encrypted at Rest)
# ============================================================
resource "aws_s3_bucket" "vehicle_docs" {
  bucket        = "${var.project_name}-vehicle-docs-${var.environment}"
  force_destroy = var.environment == "dev" ? true : false

  tags = { Name = "${var.project_name}-vehicle-docs" }
}

resource "aws_s3_bucket_versioning" "vehicle_docs" {
  bucket = aws_s3_bucket.vehicle_docs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "vehicle_docs" {
  bucket = aws_s3_bucket.vehicle_docs.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.data_key.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "vehicle_docs" {
  bucket                  = aws_s3_bucket.vehicle_docs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "vehicle_docs" {
  bucket = aws_s3_bucket.vehicle_docs.id

  rule {
    id     = "archive-old-docs"
    status = "Enabled"
    
    filter {}

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# ============================================================
# SQS: Dead Letter Queue for Failed Lambda Invocations
# ============================================================
resource "aws_sqs_queue" "dlq" {
  name                      = "${var.project_name}-ingestion-dlq"
  message_retention_seconds = 1209600 # 14 days
  kms_master_key_id         = aws_kms_key.data_key.id

  tags = { Name = "${var.project_name}-dlq" }
}

# ============================================================
# Secrets Manager: Snowflake Credentials (No Hardcoding)
# ============================================================
resource "aws_secretsmanager_secret" "snowflake_creds" {
  name        = "${var.project_name}/snowflake-credentials"
  description = "Snowflake connection credentials for the ingestion Lambda"
  kms_key_id  = aws_kms_key.data_key.arn

  tags = { Name = "${var.project_name}-sf-creds" }
}

resource "aws_secretsmanager_secret_version" "snowflake_creds" {
  secret_id = aws_secretsmanager_secret.snowflake_creds.id
  secret_string = jsonencode({
    account   = var.snowflake_account
    user      = var.snowflake_user
    password  = var.snowflake_password
    role      = "CORTEX_DEV_ROLE"
    warehouse = "AI_PROJECT_WH"
    database  = "AI_PROJECT_DB"
    schema    = "STAGING"
  })
}

# ============================================================
# IAM: Lambda Execution Role (Least Privilege)
# ============================================================
resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_permissions" {
  name = "${var.project_name}-lambda-permissions"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3ReadAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.vehicle_docs.arn,
          "${aws_s3_bucket.vehicle_docs.arn}/*"
        ]
      },
      {
        Sid    = "KMSDecrypt"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = [aws_kms_key.data_key.arn]
      },
      {
        Sid    = "SecretsManagerRead"
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue"]
        Resource = [aws_secretsmanager_secret.snowflake_creds.arn]
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Sid    = "DLQWrite"
        Effect = "Allow"
        Action = ["sqs:SendMessage"]
        Resource = [aws_sqs_queue.dlq.arn]
      }
    ]
  })
}

# ============================================================
# Lambda: PDF Ingestion Processor
# ============================================================
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/.build/lambda.zip"
}

resource "aws_lambda_function" "pdf_ingestor" {
  function_name    = "${var.project_name}-pdf-ingestor"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.11"
  timeout          = 120
  memory_size      = 512
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      SNOWFLAKE_SECRET_ARN = aws_secretsmanager_secret.snowflake_creds.arn
      ENVIRONMENT          = var.environment
    }
  }

  dead_letter_config {
    target_arn = aws_sqs_queue.dlq.arn
  }

  tracing_config {
    mode = "Active" # X-Ray tracing for observability
  }

  tags = { Name = "${var.project_name}-pdf-ingestor" }
}

# ============================================================
# S3 → Lambda Event Trigger
# ============================================================
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pdf_ingestor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.vehicle_docs.arn
}

resource "aws_s3_bucket_notification" "pdf_trigger" {
  bucket = aws_s3_bucket.vehicle_docs.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.pdf_ingestor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "incoming/"
    filter_suffix       = ".pdf"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}

# ============================================================
# IAM: Snowflake Storage Integration Role
# (Snowflake assumes this role to read from S3)
# ============================================================
resource "aws_iam_role" "snowflake_s3_access" {
  name = "${var.project_name}-snowflake-s3-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        AWS = var.snowflake_iam_user_arn
      }
      Action = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "sts:ExternalId" = var.snowflake_external_id
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "snowflake_s3_read" {
  name = "${var.project_name}-snowflake-s3-read"
  role = aws_iam_role.snowflake_s3_access.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.vehicle_docs.arn,
          "${aws_s3_bucket.vehicle_docs.arn}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [aws_kms_key.data_key.arn]
      }
    ]
  })
}
