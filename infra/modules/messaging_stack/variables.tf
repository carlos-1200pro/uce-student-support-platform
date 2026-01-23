variable "subnet_id" {
  type = string
}

variable "sg_kafka_id" {
  type = string
}

variable "sg_rabbit_id" {
  type = string
}

variable "key_name" {
  type = string
}

variable "instance_type" {
  type = string
}

variable "private_ip" {
  type    = string
  default = null
}

variable "tags" {
  type    = map(string)
  default = {}
}
