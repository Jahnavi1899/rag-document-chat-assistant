# terraform/main.tf

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Local variables
locals {
  app_name = "rag-chat"
  common_tags = {
    Application = local.app_name
    Environment = var.environment
  }
}

# Use the networking module
module "networking" {
  source = "./modules/networking"

  app_name           = local.app_name
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
}

# Use the storage module
module "storage" {
  source = "./modules/storage"

  app_name           = local.app_name
  environment        = var.environment
  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids

  allowed_security_group_ids = [
    module.ecs.backend_security_group_id,
    module.ecs.worker_security_group_id
  ]

  tags = local.common_tags
}

# Database Module
module "database" {
  source = "./modules/database"

  app_name           = local.app_name
  environment        = var.environment
  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids

  db_instance_class = "db.t3.micro"
  db_name           = var.db_name
  db_username       = var.db_username
  db_password       = var.db_password

  #ECS security group can access database
  allowed_security_group_ids = [
    module.ecs.backend_security_group_id,
    module.ecs.worker_security_group_id
  ]

  tags = local.common_tags
}

# Cache Module (ElastiCache Redis)
module "cache" {
  source = "./modules/cache"

  app_name           = local.app_name
  environment        = var.environment
  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids

  node_type       = "cache.t3.micro"
  num_cache_nodes = 1

  allowed_security_group_ids = [
    module.ecs.backend_security_group_id,
    module.ecs.worker_security_group_id
  ]

  tags = local.common_tags
}

# ALB Module (Application Load Balancer)
module "alb" {
  source = "./modules/alb"

  app_name          = local.app_name
  environment       = var.environment
  vpc_id            = module.networking.vpc_id
  public_subnet_ids = module.networking.public_subnet_ids

  tags = local.common_tags
}

# ECS Module (Container Orchestration)
module "ecs" {
  source = "./modules/ecs"

  app_name           = local.app_name
  environment        = var.environment
  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids

  # ALB connections
  alb_security_group_id     = module.alb.alb_security_group_id
  frontend_target_group_arn = module.alb.frontend_target_group_arn
  backend_target_group_arn  = module.alb.backend_target_group_arn

  # Database connections
  db_host     = module.database.db_address
  db_port     = tostring(module.database.db_port)
  db_name     = module.database.db_name
  db_username = var.db_username
  db_password = var.db_password

  # Redis connections
  redis_host = module.cache.redis_endpoint
  redis_port = tostring(module.cache.redis_port)

  # S3 bucket
  s3_bucket_name = module.storage.s3_bucket_name

  # EFS file system
  efs_file_system_id    = module.storage.efs_file_system_id
  efs_security_group_id = module.storage.efs_security_group_id

  # Docker images (placeholders for now)
  frontend_image = "nginx:latest"
  backend_image  = "nginx:latest"
  worker_image   = "nginx:latest"

  tags = local.common_tags
}
