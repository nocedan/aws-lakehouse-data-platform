# resource "aws_glue_workflow" "example" {
#   name = "dvdrentals-workflow"
# }

# resource "aws_glue_trigger" "example-start" {
#   name          = "trigger-start"
#   type          = "ON_DEMAND"
#   workflow_name = aws_glue_workflow.example.name

#   actions {
#     job_name = "dvdrentals-extraction-tf"
#   }
# }

# resource "aws_glue_job" "etl_job" {
#   name              = "dvdrentals-extraction-tf"
#   description       = "An example Glue ETL job"
#   role_arn          = aws_iam_role.glue_job_role.arn
#   glue_version      = "5.0"
#   max_retries       = 0
#   timeout           = 2880
#   number_of_workers = 2
#   worker_type       = "G.1X"
#   connections       = [aws_glue_connection.postgres_connection.name]
#   execution_class   = "STANDARD"

#   command {
#     script_location = "s3://${module.s3_bucket_glue_scripts.s3_bucket_id}/jobs/etl_job.py"
#     name            = "glueetl"
#     python_version  = "3"
#   }

#   notification_property {
#     notify_delay_after = 3 # delay in minutes
#   }

#   default_arguments = {
#     "--job-language"                     = "python"
#     "--continuous-log-logGroup"          = "/aws-glue/jobs"
#     "--enable-continuous-cloudwatch-log" = "true"
#     "--enable-continuous-log-filter"     = "true"
#     "--enable-metrics"                   = ""
#     "--enable-auto-scaling"              = "true"
#   }

#   execution_property {
#     max_concurrent_runs = 1
#   }

#   tags = {
#     "ManagedBy" = "AWS"
#   }
# }

# # IAM role for Glue jobs
# resource "aws_iam_role" "glue_job_role" {
#   name = "glue-job-role"

#   assume_role_policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [
#       {
#         Action = "sts:AssumeRole"
#         Effect = "Allow"
#         Principal = {
#           Service = "glue.amazonaws.com"
#         }
#       }
#     ]
#   })
# }

# resource "aws_s3_object" "glue_etl_script" {
#   bucket = module.s3_bucket_glue_scripts.s3_bucket_id
#   key    = "jobs/etl_job.py"
#   source = "jobs/etl_job.py" # Make sure this file exists locally
# }

# resource "aws_glue_connection" "postgres_connection" {
#   name = "postgres_connection"
#   connection_properties = {
#     JDBC_CONNECTION_URL = "jdbc:postgresql://${module.db.db_instance_endpoint}/dvdrentals"
#     PASSWORD            = var.postgres_password
#     USERNAME            = var.postgres_username
#   }
#   physical_connection_requirements {
#     availability_zone      = module.vpc.azs[0]
#     security_group_id_list = [aws_security_group.main.id]  # Glue connection security group
#     subnet_id              = module.vpc.private_subnets[0]
#   }
# }