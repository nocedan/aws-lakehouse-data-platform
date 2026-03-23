module "db" {
  source = "terraform-aws-modules/rds/aws"

  identifier = "dvdrentals-database"

  engine            = "postgres"
  engine_version    = "17.6"
  instance_class    = "db.t4g.micro"
  allocated_storage = 1

  db_name  = "dvdrentals"
  username = var.postgres_username
  port     = "5432"

  iam_database_authentication_enabled = true

  vpc_security_group_ids = [aws_security_group.main.id]  # RDS security group

  maintenance_window = "Mon:00:00-Mon:03:00"
  backup_window      = "03:00-06:00"

  # Enhanced Monitoring - see example for details on how to create the role
  # by yourself, in case you don't want to create it automatically
  monitoring_interval    = "30"
  monitoring_role_name   = "MyRDSMonitoringRole"
  create_monitoring_role = true

  tags = {
    Owner       = "user"
    Environment = "dev"
  }

  # DB subnet group
  create_db_subnet_group = true
  subnet_ids             = [module.vpc.private_subnets[0]]

  # DB parameter group
  family = "postgres17"

  # DB option group
  major_engine_version = "17"

  # Database Deletion Protection
  deletion_protection = true
}