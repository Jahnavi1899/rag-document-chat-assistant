# modules/ecs/variables.tf

variable "app_name" {
  description = "Application name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "Security group ID of the ALB"
  type        = string
}

variable "frontend_target_group_arn" {
  description = "ARN of the frontend target group"
  type        = string
}

variable "backend_target_group_arn" {
  description = "ARN of the backend target group"
  type        = string
}

# Database connection info
variable "db_host" {
  description = "Database host"
  type        = string
}

variable "db_port" {
  description = "Database port"
  type        = string
}

variable "db_name" {
  description = "Database name"
  type        = string
}

variable "db_username" {
  description = "Database username"
  type        = string
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "openai_key_parameter_name" {
  description = "Parameter Store name for OpenAI API key"
  type        = string
  default     = "/rag-chat/dev/openai-api-key"
}

# Redis connection info
variable "redis_host" {
  description = "Redis host"
  type        = string
}

variable "redis_port" {
  description = "Redis port"
  type        = string
}

# S3 bucket
variable "s3_bucket_name" {
  description = "S3 bucket name for documents"
  type        = string
}

# EFS file system
variable "efs_file_system_id" {
  description = "EFS file system ID for ChromaDB"
  type        = string
}

variable "efs_security_group_id" {
  description = "EFS security group ID"
  type        = string
}

# Container images (will use placeholder for now)
variable "frontend_image" {
  description = "Docker image for frontend"
  type        = string
  default     = "nginx:latest" # Placeholder
}

variable "backend_image" {
  description = "Docker image for backend"
  type        = string
  default     = "nginx:latest" # Placeholder
}

variable "worker_image" {
  description = "Docker image for worker"
  type        = string
  default     = "nginx:latest" # Placeholder
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}