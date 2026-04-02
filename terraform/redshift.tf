resource "aws_redshiftserverless_namespace" "my_redshift_namespace" {
  namespace_name = "redshift-serverless-namespace"
  region = var.region

    # Adicionar a role aqui
  default_iam_role_arn = aws_iam_role.redshift_spectrum_role.arn
  iam_roles            = [aws_iam_role.redshift_spectrum_role.arn]
}

resource "aws_redshiftserverless_workgroup" "redshift" {
  namespace_name = aws_redshiftserverless_namespace.my_redshift_namespace.namespace_name
  workgroup_name = "redshift-serverless-workgroup"

  region = var.region
  port = 5439
  publicly_accessible = true
  security_group_ids = [aws_security_group.main.id]  # Redshift security group
  subnet_ids = module.vpc.public_subnets  # Redshift subnets, can be public or private depending on your needs
}

# Note: Redshift Serverless does not support IAM roles for Redshift Spectrum, 
#but you can create an IAM role for Glue to access S3 and use it in your Glue jobs that interact with Redshift Spectrum.
resource "aws_iam_role" "redshift_spectrum_role" {
  name = "redshift-spectrum-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RedshiftAssumeRole"
        Effect = "Allow"
        Principal = {
          Service = ["redshift.amazonaws.com", "redshift-serverless.amazonaws.com"]
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

data "aws_iam_policy" "redshift_full_access" {
  arn = "arn:aws:iam::aws:policy/AmazonRedshiftAllCommandsFullAccess"
}

data "aws_iam_policy" "redshift_full_access_two" {
  arn = "arn:aws:iam::aws:policy/AmazonRedshiftFullAccess"
}

resource "aws_iam_policy" "redshift_spectrum_policy" {
  name        = "redshift-spectrum-policy"
  description = "Allows Redshift Serverless to query external tables via Spectrum and Glue Data Catalog"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "GlueAccess"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:CreateDatabase",
          "glue:GetTable",
          "glue:GetTables",
          "glue:CreateTable",
          "glue:GetPartition",
          "glue:GetPartitions",
          "glue:BatchGetPartition",      # needed for partition pruning
          "glue:GetUserDefinedFunction",
          "glue:GetUserDefinedFunctions"
        ]
        Resource = "*"
      },
      {
        Sid    = "S3Access"
        Effect = "Allow"
        Action = [
                "s3:GetObject",
                "s3:GetBucketAcl",
                "s3:GetBucketCors",
                "s3:GetEncryptionConfiguration",
                "s3:GetBucketLocation",
                "s3:ListBucket",
                "s3:ListAllMyBuckets",
                "s3:ListMultipartUploadParts",
                "s3:ListBucketMultipartUploads",
                "s3:PutObject",
                "s3:PutBucketAcl",
                "s3:PutBucketCors",
                "s3:DeleteObject",
                "s3:AbortMultipartUpload",
                "s3:CreateBucket"
            ],
        Resource = [
          "arn:aws:s3:::${var.datalake_bucket_name}",
          "arn:aws:s3:::${var.datalake_bucket_name}/*"
        ]
      },
      {
        Sid    = "S3ListAllBuckets"
        Effect = "Allow"
        Action = [
          "s3:ListAllMyBuckets"          # Spectrum probes this on startup
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

resource "aws_iam_role_policy_attachment" "attach_policies1" {
  role       = aws_iam_role.redshift_spectrum_role.name
  policy_arn = aws_iam_policy.redshift_spectrum_policy.arn
}

resource "aws_iam_role_policy_attachment" "attach_policies2" {
  role       = aws_iam_role.redshift_spectrum_role.name
  policy_arn = data.aws_iam_policy.redshift_full_access.arn
}

resource "aws_iam_role_policy_attachment" "attach_policies3" {
  role       = aws_iam_role.redshift_spectrum_role.name
  policy_arn = data.aws_iam_policy.redshift_full_access_two.arn
}

# ✅ FIX 3 — Lake Formation: permissão explícita no banco "dvdrentals"
resource "aws_lakeformation_permissions" "redshift_dvdrentals_db" {
  principal   = aws_iam_role.redshift_spectrum_role.arn
  permissions = ["ALL"]

  database {
    name = "dvdrentals"
  }

  # ✅ ADD THIS
  depends_on = [aws_lakeformation_data_lake_settings.glue_admin]
}

# # ✅ ADD THIS — grant on all tables and its columns inside dvdrentals
# resource "aws_lakeformation_permissions" "redshift_dvdrentals_tables" {
#   principal   = aws_iam_role.redshift_spectrum_role.arn
#   permissions = ["DESCRIBE"]

#   table {
#     database_name = "dvdrentals"
#     wildcard      = true   # covers every table, including future ones
#   }

#   depends_on = [aws_lakeformation_permissions.redshift_dvdrentals_db]
# }

# # Column level access

# locals {
#   tables = ["category", "film_category", "film", "customer", "rental", "inventory"]  # list all tables in dvdrentals
# }

# # Grant column-level SELECT on each table (all columns via wildcard)
# resource "aws_lakeformation_permissions" "all_columns" {
#   for_each  = toset(local.tables)
#   principal = aws_iam_role.redshift_spectrum_role.arn

#   table_with_columns {
#     database_name = "dvdrentals"
#     name          = each.value
#     wildcard = true  # grants permissions on all columns of the table
#   }

#   permissions = ["SELECT"]
# }

# Lake formation permissions for Redshift Serverless role
resource "aws_lakeformation_permissions" "data_location_access" {
  principal   = aws_iam_role.redshift_spectrum_role.arn
  permissions = ["DATA_LOCATION_ACCESS"]

  data_location {
    arn = module.s3_bucket.s3_bucket_arn
  }

  depends_on = [aws_lakeformation_data_lake_settings.glue_admin]
}