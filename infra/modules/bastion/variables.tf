variable "subnet_id" {
  type = string
}

variable "sg_id" {
  type = string
}

variable "key_name" {
  type = string
}

variable "instance_type" {
  type = string
}

variable "vpc_cidr" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
