# ============================================================
# Variables: Parameterized for Multi-Environment Deployment
# ============================================================

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "project_name" {
  description = "Project identifier used for resource naming"
  type        = string
  default     = "automotive-copilot"
}

variable "owner_email" {
  description = "Email of the resource owner (for tagging)"
  type        = string
}

# Snowflake Connection (passed securely via tfvars or CI/CD)
variable "snowflake_account" {
  description = "Snowflake account identifier"
  type        = string
  sensitive   = true
}

variable "snowflake_user" {
  description = "Snowflake username for Lambda"
  type        = string
  sensitive   = true
}

variable "snowflake_password" {
  description = "Snowflake password for Lambda"
  type        = string
  sensitive   = true
}

# These values come from running DESC INTEGRATION in Snowflake
# after creating the storage integration (see snowflake/ SQL files)
variable "snowflake_iam_user_arn" {
  description = "The IAM User ARN from Snowflake's STORAGE_AWS_IAM_USER_ARN (from DESC INTEGRATION)"
  type        = string
  default     = "arn:aws:iam::032441996083:user/fqqg1000-s"
}

variable "snowflake_external_id" {
  description = "The External ID from Snowflake's STORAGE_AWS_EXTERNAL_ID (from DESC INTEGRATION)"
  type        = string
  default     = "EZ42659_SFCRole=4_Et9unOpKwLzTGW61iH9+LtHefO4="
}
