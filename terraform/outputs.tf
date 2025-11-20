# terraform/outputs.tf

# Networking Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.networking.public_subnet_ids
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.networking.private_subnet_ids
}

# Storage Outputs
output "s3_bucket_name" {
  description = "S3 bucket name for documents"
  value       = module.storage.s3_bucket_name
}

output "efs_file_system_id" {
  description = "EFS file system ID"
  value       = module.storage.efs_file_system_id
}

# Database Outputs
output "db_endpoint" {
  description = "Database endpoint"
  value       = module.database.db_endpoint
}

output "db_address" {
  description = "Database address"
  value       = module.database.db_address
}

# Cache Outputs
output "redis_endpoint" {
  description = "Redis endpoint"
  value       = module.cache.redis_endpoint
}

output "redis_connection_string" {
  description = "Redis connection string"
  value       = module.cache.redis_connection_string
  sensitive   = true
}

# ALB Outputs
output "alb_dns_name" {
  description = "ALB DNS name - use this to access your application"
  value       = module.alb.alb_dns_name
}

output "application_url" {
  description = "Application URL"
  value       = "http://${module.alb.alb_dns_name}"
}

# ECS Outputs
output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "frontend_service_name" {
  description = "Frontend service name"
  value       = module.ecs.frontend_service_name
}

output "backend_service_name" {
  description = "Backend service name"
  value       = module.ecs.backend_service_name
}

output "worker_service_name" {
  description = "Worker service name"
  value       = module.ecs.worker_service_name
}