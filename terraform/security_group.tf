resource "aws_security_group" "main" {
  name        = "dvdrentals-sg"
  description = "Security Group for RDS, Glue and Redshift"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "Postgres - Glue only"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    self        = true  # permite tráfego entre recursos do mesmo SG
  }

  ingress {
    description = "Redshift - authorized IPs only"
    from_port   = 5439
    to_port     = 5439
    protocol    = "tcp"
    cidr_blocks = var.authorized_ips
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "dvdrentals-sg" }
}