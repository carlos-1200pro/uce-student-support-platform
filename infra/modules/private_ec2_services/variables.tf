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

variable "service_pairs" {
  type = list(object({
    service_a = string
    port_a    = number
    service_b = string
    port_b    = number
  }))
}

variable "service_images" {
  type = map(string)
}

variable "service_base_paths" {
  type = map(string)
}

variable "db_host" {
  type = string
}

variable "db_name" {
  type = string
}

variable "db_user" {
  type = string
}

variable "db_password" {
  type = string
}

variable "redis_host" {
  type = string
}

variable "mongo_host" {
  type = string
}

variable "kafka_bootstrap" {
  type = string
}

variable "rabbitmq_host" {
  type = string
}

variable "jwt_secret" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
