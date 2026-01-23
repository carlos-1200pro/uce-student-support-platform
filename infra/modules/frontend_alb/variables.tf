variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "sg_id" {
  type = string
}

variable "targets" {
  type = list(object({
    name        = string
    port        = number
    path        = string
    instance_id = string
  }))
}

variable "tags" {
  type    = map(string)
  default = {}
}
