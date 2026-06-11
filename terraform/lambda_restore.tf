# Container-image Lambda that restores the dvdrental dump into RDS.
# Deployed in the VPC private subnets so it can reach the private RDS
# instance; invoked by `scripts/deploy.py restore-db`.
# Building/pushing the image requires a local Docker daemon at apply time.

resource "aws_ecr_repository" "restore_db" {
  name         = "dvdrentals-restore-db"
  force_delete = true # allows terraform destroy even with images pushed
}

locals {
  restore_lambda_src = "${path.module}/../lambda/restore_db"
  # Content-addressed tag: a new image is built and the Lambda updated only
  # when the Dockerfile or handler change
  restore_image_tag = sha1(join("", [
    filesha1("${local.restore_lambda_src}/Dockerfile"),
    filesha1("${local.restore_lambda_src}/handler.py"),
  ]))
  restore_image_uri = "${aws_ecr_repository.restore_db.repository_url}:${local.restore_image_tag}"
  ecr_registry      = split("/", aws_ecr_repository.restore_db.repository_url)[0]
}

resource "terraform_data" "restore_db_image" {
  triggers_replace = local.restore_image_tag

  provisioner "local-exec" {
    interpreter = ["bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      aws ecr get-login-password --region ${var.region} | docker login --username AWS --password-stdin ${local.ecr_registry}
      docker buildx build --platform linux/amd64 --provenance=false -t ${local.restore_image_uri} ${local.restore_lambda_src}
      docker push ${local.restore_image_uri}
    EOT
  }

  depends_on = [aws_ecr_repository.restore_db]
}

resource "aws_iam_role" "restore_lambda_role" {
  name = "dvdrentals-restore-db-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# ENI management for VPC attachment + CloudWatch Logs
resource "aws_iam_role_policy_attachment" "restore_lambda_vpc" {
  role       = aws_iam_role.restore_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "restore_lambda_s3" {
  name = "restore-db-backup-read"
  role = aws_iam_role.restore_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "arn:aws:s3:::${var.datalake_bucket_name}/rds-database-backups/*"
      }
    ]
  })
}

resource "aws_lambda_function" "restore_db" {
  function_name = "dvdrentals-restore-db"
  role          = aws_iam_role.restore_lambda_role.arn
  package_type  = "Image"
  image_uri     = local.restore_image_uri
  architectures = ["x86_64"]
  timeout       = 900
  memory_size   = 1024

  # aws_security_group.main's self-referencing 5432 rule grants RDS access
  vpc_config {
    subnet_ids         = module.vpc.private_subnets
    security_group_ids = [aws_security_group.main.id]
  }

  # Plaintext password in env mirrors the existing trade-off in the Glue
  # connection properties (glue.tf); avoids a Secrets Manager VPC endpoint
  environment {
    variables = {
      DB_HOST       = module.db.db_instance_address
      DB_PORT       = "5432"
      DB_USER       = local.db_credentials["username"]
      DB_PASSWORD   = local.db_credentials["password"]
      DB_NAME       = "dvdrentals"
      BACKUP_BUCKET = module.s3_bucket.s3_bucket_id
      BACKUP_KEY    = aws_s3_object.rds_database_backups.key
    }
  }

  depends_on = [terraform_data.restore_db_image]
}
