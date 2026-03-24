resource "aws_security_group" "main" {
  name        = "dvdrentals-sg"
  description = "Security Group for RDS, Glue and Redshift"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "Postgres - Glue only"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    self        = true
  }

  ingress {
    description = "Glue self-referencing - all ports"
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    self        = true
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