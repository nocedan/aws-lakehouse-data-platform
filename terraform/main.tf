provider "aws" {
  region = var.region
}



# resource "aws_instance" "app_server" {
#   ami           = data.aws_ami.ubuntu.id
#   instance_type = var.instance_type

#     vpc_security_group_ids = [module.vpc.default_security_group_id]
#     subnet_id = module.vpc.public_subnets[0]

#   tags = {
#     Name = var.instance_name
#   }
# }
