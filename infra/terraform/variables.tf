variable "service_name" {
  description = "Nombre del módulo o servicio"
  type        = string
}

variable "instance_count" {
  description = "Cantidad de instancias EC2 a crear"
  type        = number
  default     = 1
}
