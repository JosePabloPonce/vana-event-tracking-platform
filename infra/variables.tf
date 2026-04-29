variable "aws_region" {
  description = "AWS region where resources will be deployed"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "vana-events"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "event_api_key" {
  description = "Simple API key required by the ingestion Lambda"
  type        = string
  sensitive   = true
}