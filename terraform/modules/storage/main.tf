# modules/storage/main.tf

# S3 bucket for storing uploaded documents
resource "aws_s3_bucket" "documents" {
  bucket = "${var.app_name}-${var.environment}-documents-${data.aws_caller_identity.current.account_id}"

  tags = merge(
    var.tags,
    {
      Name = "${var.app_name}-${var.environment}-documents"
    }
  )
}

# Block public access to S3 bucket (security best practice)
resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning (keeps history of objects)
resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption at rest
resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# EFS file system for ChromaDB (shared storage between backend and worker)
resource "aws_efs_file_system" "chromadb" {
  creation_token = "${var.app_name}-${var.environment}-chromadb"
  encrypted      = true

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.app_name}-${var.environment}-chromadb-efs"
    }
  )
}

# Security group for EFS
resource "aws_security_group" "efs" {
  name        = "${var.app_name}-${var.environment}-efs-sg"
  description = "Security group for EFS mount targets"
  vpc_id      = var.vpc_id

  ingress {
    description     = "NFS from ECS tasks"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = var.allowed_security_group_ids
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.app_name}-${var.environment}-efs-sg"
    }
  )
}

# EFS Mount Targets (one per private subnet for high availability)
resource "aws_efs_mount_target" "chromadb" {
  count = length(var.private_subnet_ids)

  file_system_id  = aws_efs_file_system.chromadb.id
  subnet_id       = var.private_subnet_ids[count.index]
  security_groups = [aws_security_group.efs.id]
}

# Data source to get current AWS account ID
data "aws_caller_identity" "current" {}