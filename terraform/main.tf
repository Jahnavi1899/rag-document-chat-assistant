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

  app_name           = "rag-chat"
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
}

# Use the storage module
module "storage" {
  source = "./modules/storage"

  app_name           = "rag-chat"
  environment        = var.environment
  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  
  allowed_security_group_ids = []
  
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
  
  # Will add ECS security group later
  allowed_security_group_ids = []
  
  tags = local.common_tags
}

