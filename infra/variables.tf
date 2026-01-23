variable "region" {
  type        = string
  description = "AWS region"
}

variable "azs" {
  type        = list(string)
  description = "Availability zones"
}

variable "lab1_vpc_cidr" {
  type        = string
  description = "VPC CIDR for lab-module1"
}

variable "lab2_vpc_cidr" {
  type        = string
  description = "VPC CIDR for lab-module2"
}

variable "lab1_public_subnet_cidrs" {
  type        = list(string)
  description = "Public subnet CIDRs for lab-module1"
}

variable "lab1_private_subnet_cidrs" {
  type        = list(string)
  description = "Private subnet CIDRs for lab-module1"
}

variable "lab1_data_private_ip" {
  type        = string
  description = "Fixed private IP for data-stack (optional)"
  default     = null
}

variable "lab1_messaging_private_ip" {
  type        = string
  description = "Fixed private IP for messaging-stack (optional)"
  default     = null
}

variable "lab2_public_subnet_cidrs" {
  type        = list(string)
  description = "Public subnet CIDRs for lab-module2"
}

variable "lab2_private_subnet_cidrs" {
  type        = list(string)
  description = "Private subnet CIDRs for lab-module2"
}

variable "enable_nat_gateway" {
  type        = bool
  description = "Enable NAT Gateway in lab-module1"
  default     = true
}


variable "my_ip_cidr" {
  type        = string
  description = "Your public IP CIDR for Bastion access"
}

variable "lab1_key_name" {
  type        = string
  description = "EC2 key pair name for lab-module1"
}

variable "lab2_key_name" {
  type        = string
  description = "EC2 key pair name for lab-module2"
}

variable "instance_type_gateway" {
  type        = string
  description = "Instance type for API Gateway EC2"
}

variable "lab1_gateway_eip_allocation_id" {
  type        = string
  description = "Existing EIP allocation ID for the API Gateway (optional)"
  default     = ""
}

variable "instance_type_bastion" {
  type        = string
  description = "Instance type for Bastion EC2"
}

variable "instance_type_services" {
  type        = string
  description = "Instance type for microservice EC2s"
}

variable "instance_type_data" {
  type        = string
  description = "Instance type for data stack EC2"
}

variable "instance_type_kafka" {
  type        = string
  description = "Instance type for messaging EC2"
}

variable "instance_type_frontend" {
  type        = string
  description = "Instance type for frontend EC2s"
}


variable "microservice_ports" {
  type        = list(number)
  description = "Ports exposed by microservices behind the internal ALB"
  default     = [8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009, 8010]
}

variable "postgres_db" {
  type        = string
  description = "Postgres database name"
}

variable "postgres_user" {
  type        = string
  description = "Postgres user"
}

variable "postgres_password" {
  type        = string
  description = "Postgres password"
}

variable "jwt_secret" {
  type        = string
  description = "JWT secret shared by microservices"
}

variable "tags" {
  type        = map(string)
  description = "Common tags"
  default     = {}
}
