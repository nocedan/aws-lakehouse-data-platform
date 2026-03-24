variable "datalake_bucket_name" {
  description = "Name of the S3 bucket to create"
  type        = string
  default     = "terraform-data-lake-bucket"
}

variable "glue_scripts_bucket_name" {
  description = "Name of the S3 bucket to store Glue scripts"
  type        = string
  default     = "terraform-glue-scripts-bucket"
}

variable region {
  description = "AWS region to deploy resources in"
  type        = string
  default     = "us-west-2"
}

variable "postgres_username" {
    description = "Username for the PostgreSQL database"
    type        = string
    default     = "postgres_master_user"
}

variable "postgres_password" {
    description = "Password for the PostgreSQL database"
    type        = string
    default     = "password"
}

variable "authorized_ips" {
  description = "List of authorized IPs for Redshift access"
  type        = list(string)
  default     = ["179.135.247.101/32"] # Permite acesso de IP específico (substitua pelo seu IP ou faixa de IPs autorizados)
  #Para encontrar seu IP público:
  # (Invoke-WebRequest -Uri "https://checkip.amazonaws.com").Content.Trim()
}