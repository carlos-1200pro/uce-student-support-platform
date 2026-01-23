variable "vpc_id" {
  type = string
}

variable "vpc_cidr" {
  type = string
}

variable "my_ip_cidr" {
  type = string
}

variable "microservice_ports" {
  type = list(number)
}

variable "tags" {
  type    = map(string)
  default = {}
}
