variable "aws_profile" {
  description = "AWS profile to use"
  type        = string
}

provider "aws" {
  profile = var.aws_profile
  region  = "us-east-1"
}
