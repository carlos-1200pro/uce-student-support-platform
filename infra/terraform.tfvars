region = "us-east-1"
azs    = ["us-east-1a", "us-east-1b"]

lab1_vpc_cidr             = "10.10.0.0/16"
lab1_public_subnet_cidrs  = ["10.10.1.0/24", "10.10.2.0/24"]
lab1_private_subnet_cidrs = ["10.10.11.0/24", "10.10.12.0/24"]
lab1_data_private_ip      = "10.10.11.25"
lab1_messaging_private_ip = "10.10.12.238"

lab2_vpc_cidr             = "10.20.0.0/16"
lab2_public_subnet_cidrs  = ["10.20.1.0/24", "10.20.2.0/24"]
lab2_private_subnet_cidrs = ["10.20.11.0/24", "10.20.12.0/24"]

enable_nat_gateway  = false
my_ip_cidr          = "59.153.47.119/32"

lab1_key_name = "uce-lab1-key"
lab2_key_name = "uce-lab2-key"

instance_type_gateway  = "t3.micro"
instance_type_bastion  = "t3.micro"
instance_type_services = "t3.small"
instance_type_data     = "t3.small"
instance_type_kafka    = "t3.medium"
instance_type_frontend = "t3.micro"

postgres_db       = "student_platform"
postgres_user     = "postgres"
postgres_password = "carlos1212"

jwt_secret = "carlos1212"

tags = {
  project = "uce-student-support-platform"
  env     = "qa"
}
