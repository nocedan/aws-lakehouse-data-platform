# output "instance_hostname" {
#   description = "Public DNS name of the EC2 instance"
#   value       = aws_instance.app_server.public_dns
# }

output "bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = module.s3_bucket.s3_bucket_arn
}

output "bucket_id" {
  description = "ID of the S3 bucket"
  value       = module.s3_bucket.s3_bucket_id
}

output db_username {
  description = "Username for the PostgreSQL database"
  value       = module.db.db_instance_username
  sensitive = true
}

output "db_password" {
  description = "Password for the PostgreSQL database"
  value       = module.db.db_instance_master_user_secret_arn
  sensitive = true
}

output "db_endpoint" {
  value       = module.db.db_instance_endpoint
  description = "The connection endpoint"
}

output "db_hostname" {
  value       = module.db.db_instance_name
  description = "The address of the RDS instance"
}

output "db_port" {
    value       = module.db.db_instance_port
    description = "The port on which the database accepts connections"
}

# output "redshift_endpoint" {
#   value       = aws_redshiftserverless_workgroup.redshift.endpoint
#   description = "The connection endpoint for the Redshift Serverless workgroup"
# }

# output "redshift_workgroup_name" {
#   value       = aws_redshiftserverless_workgroup.redshift.workgroup_name
#   description = "The name of the Redshift Serverless workgroup"
# }

# output "redshift_spectrum_role_arn" {
#   value       = aws_iam_role.redshift_spectrum_role.arn
#   description = "ARN of the IAM role for Redshift Spectrum"
# }