module "s3_bucket" {
    source = "terraform-aws-modules/s3-bucket/aws"
    version = "3.0.0"

    bucket = "${var.datalake_bucket_name}"
    acl    = "private"
}

resource "aws_s3_object" "landing_layer" {
  bucket  = module.s3_bucket.s3_bucket_id
  key     = "landing-layer/"
  content = ""
}

resource "aws_s3_object" "transformation_layer" {
  bucket  = module.s3_bucket.s3_bucket_id
  key     = "transformation-layer/"
  content = ""
}

resource "aws_s3_object" "serving_layer" {
  bucket  = module.s3_bucket.s3_bucket_id
  key     = "serving-layer/"
  content = ""
}

module "s3_bucket_glue_scripts" {
    source = "terraform-aws-modules/s3-bucket/aws"
    version = "3.0.0"

    bucket = "${var.glue_scripts_bucket_name}"
    acl    = "private"
}