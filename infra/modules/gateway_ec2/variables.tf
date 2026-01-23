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

variable "upstream_host" {
  type = string
}

variable "eip_allocation_id" {
  type    = string
  default = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}
