variable "subnet_id" {
  type = string
}

variable "sg_db_id" {
  type = string
}

variable "sg_redis_id" {
  type = string
}

variable "sg_mongo_id" {
  type = string
}

variable "key_name" {
  type = string
}

variable "instance_type" {
  type = string
}

variable "postgres_db" {
  type = string
}

variable "postgres_user" {
  type = string
}

variable "postgres_password" {
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
