resource "aws_glue_workflow" "dvdrentals_workflow" {
  name = "dvdrentals-workflow"
}

resource "aws_glue_trigger" "example-start" {
  name          = "trigger-start"
  type          = "ON_DEMAND"
  workflow_name = aws_glue_workflow.dvdrentals_workflow.name

  actions {
    job_name = "dvdrentals-extraction-tf"
  }
}

# IAM role for Glue jobs
resource "aws_iam_role" "glue_job_role" {
  name = "glue-job-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })
}

# Mandatory Glue baseline
resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_job_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# S3 access
resource "aws_iam_role_policy_attachment" "glue_s3" {
  role       = aws_iam_role.glue_job_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# Secrets Manager read-only (credentials already created)
resource "aws_iam_role_policy_attachment" "glue_secrets" {
  role       = aws_iam_role.glue_job_role.name
  policy_arn = "arn:aws:iam::aws:policy/SecretsManagerReadWrite"
}

# RDS access
resource "aws_iam_role_policy_attachment" "glue_rds" {
  role       = aws_iam_role.glue_job_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonRDSFullAccess"
}

# ✅ FIX 1 — Inline policy: Glue Catalog + Lake Formation permissions
resource "aws_iam_role_policy" "glue_catalog_lakeformation" {
  name = "glue-catalog-lakeformation"
  role = aws_iam_role.glue_job_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "GlueCatalogAccess"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetPartition",
          "glue:GetPartitions",
          "glue:CreateDatabase",
          "glue:CreateTable",
          "glue:UpdateTable",
          "glue:DeleteTable",
          "glue:BatchGetPartition"
        ]
        Resource = "*"
      },
      {
        Sid    = "LakeFormationDataAccess"
        Effect = "Allow"
        Action = [
          "lakeformation:GetDataAccess",
          "lakeformation:GrantPermissions",
          "lakeformation:GetResourceLFTags",
          "lakeformation:ListLFTags"
        ]
        Resource = "*"
      }
    ]
  })
}

# ✅ FIX 2 — Lake Formation: registra o role como admin do data lake
locals {
  lake_formation_admins = toset([
    aws_iam_role.redshift_spectrum_role.arn,  # newly added
    "arn:aws:iam::396768596145:user/adm_user",
    aws_iam_role.glue_job_role.arn,  # newly added
  ])
}

resource "aws_lakeformation_data_lake_settings" "glue_admin" {
  admins = local.lake_formation_admins
 
  allow_full_table_external_data_access = true

}

# Fetch the secret created automatically by RDS
data "aws_secretsmanager_secret_version" "db" {
  secret_id = module.db.db_instance_master_user_secret_arn
}

locals {
  db_credentials = jsondecode(data.aws_secretsmanager_secret_version.db.secret_string)
}

resource "aws_glue_connection" "postgres_connection" {
  name = "postgres_connection"

  connection_properties = {
    JDBC_CONNECTION_URL = "jdbc:postgresql://${module.db.db_instance_endpoint}/dvdrentals"
    USERNAME            = local.db_credentials["username"]
    PASSWORD            = local.db_credentials["password"]
  }

  physical_connection_requirements {
    availability_zone      = module.vpc.azs[0]
    security_group_id_list = [aws_security_group.main.id]
    subnet_id              = module.vpc.private_subnets[0]
  }
}

resource "aws_glue_catalog_database" "dvdrentals_glue_db" {
  name = "dvdrentals"

  create_table_default_permission {
    permissions = ["SELECT"]

    principal {
      data_lake_principal_identifier = "IAM_ALLOWED_PRINCIPALS"
    }
  }
}

resource "aws_glue_job" "etl_job" {
  name              = "dvdrentals-extraction-tf"
  description       = "An example Glue ETL job"
  role_arn          = aws_iam_role.glue_job_role.arn
  glue_version      = "5.0"
  max_retries       = 0
  timeout           = 2880
  number_of_workers = 2
  worker_type       = "G.1X"
  connections       = [aws_glue_connection.postgres_connection.name]
  execution_class   = "STANDARD"

  command {
    script_location = "s3://${module.s3_bucket_glue_scripts.s3_bucket_id}/jobs/etl_job.py"
    name            = "glueetl"
    python_version  = "3"
  }

  notification_property {
    notify_delay_after = 3 # delay in minutes
  }

  default_arguments = {
    "--job-language"                     = "python"
    "--continuous-log-logGroup"          = "/aws-glue/jobs"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-continuous-log-filter"     = "true"
    "--enable-metrics"                   = ""
    "--enable-auto-scaling"              = "true"
    "--enable-glue-datacatalog"          = "true"
  }

  execution_property {
    max_concurrent_runs = 1
  }

  tags = {
    "ManagedBy" = "AWS"
  }
}

resource "aws_s3_object" "glue_etl_script" {
  bucket = module.s3_bucket_glue_scripts.s3_bucket_id
  key    = "jobs/etl_job.py"
  source = "jobs/etl_job.py" # Make sure this file exists locally
}