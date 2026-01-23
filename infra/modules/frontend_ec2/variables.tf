variable "subnet_ids" {
  type = list(string)
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

variable "frontend_pairs" {
  type = list(object({
    frontend_a = string
    port_a     = number
    frontend_b = string
    port_b     = number
  }))
}

variable "frontend_images" {
  type = map(string)
}

variable "gateway_url" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
