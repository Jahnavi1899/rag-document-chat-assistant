# modules/ecs/outputs.tf

output "cluster_id" {
  description = "ID of the ECS cluster"
  value       = aws_ecs_cluster.main.id
}

output "cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "frontend_service_name" {
  description = "Name of the frontend ECS service"
  value       = aws_ecs_service.frontend.name
}

output "backend_service_name" {
  description = "Name of the backend ECS service"
  value       = aws_ecs_service.backend.name
}

output "worker_service_name" {
  description = "Name of the worker ECS service"
  value       = aws_ecs_service.worker.name
}

output "frontend_security_group_id" {
  description = "Security group ID of frontend tasks"
  value       = aws_security_group.frontend.id
}

output "backend_security_group_id" {
  description = "Security group ID of backend tasks"
  value       = aws_security_group.backend.id
}

output "worker_security_group_id" {
  description = "Security group ID of worker tasks"
  value       = aws_security_group.worker.id
}