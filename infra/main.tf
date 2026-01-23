module "lab1_network" {
  source               = "./modules/network"
  providers            = { aws = aws.lab1 }
  vpc_cidr             = var.lab1_vpc_cidr
  azs                  = var.azs
  public_subnet_cidrs  = var.lab1_public_subnet_cidrs
  private_subnet_cidrs = var.lab1_private_subnet_cidrs
  enable_nat_gateway   = var.enable_nat_gateway
  name_prefix          = "lab1"
  tags                 = var.tags
}

module "lab1_security_groups" {
  source             = "./modules/security_groups"
  providers          = { aws = aws.lab1 }
  vpc_id             = module.lab1_network.vpc_id
  vpc_cidr           = var.lab1_vpc_cidr
  my_ip_cidr         = var.my_ip_cidr
  microservice_ports = var.microservice_ports
  tags               = var.tags
}

module "lab1_bastion" {
  source        = "./modules/bastion"
  providers     = { aws = aws.lab1 }
  subnet_id     = module.lab1_network.public_subnet_ids[0]
  sg_id         = module.lab1_security_groups.sg_bastion_id
  key_name      = var.lab1_key_name
  instance_type = var.instance_type_bastion
  vpc_cidr      = var.lab1_vpc_cidr
  tags          = var.tags
}

resource "aws_route" "lab1_private_to_bastion_nat" {
  provider               = aws.lab1
  route_table_id         = module.lab1_network.private_route_table_id
  destination_cidr_block = "0.0.0.0/0"
  network_interface_id   = module.lab1_bastion.primary_network_interface_id
}

module "lab1_data_stack" {
  source            = "./modules/data_stack"
  providers         = { aws = aws.lab1 }
  subnet_id         = module.lab1_network.private_subnet_ids[0]
  sg_db_id          = module.lab1_security_groups.sg_db_id
  sg_redis_id       = module.lab1_security_groups.sg_redis_id
  sg_mongo_id       = module.lab1_security_groups.sg_mongo_id
  key_name          = var.lab1_key_name
  instance_type     = var.instance_type_data
  private_ip        = var.lab1_data_private_ip
  postgres_db       = var.postgres_db
  postgres_user     = var.postgres_user
  postgres_password = var.postgres_password
  tags              = var.tags
  depends_on        = [aws_route.lab1_private_to_bastion_nat]
}

module "lab1_messaging_stack" {
  source        = "./modules/messaging_stack"
  providers     = { aws = aws.lab1 }
  subnet_id     = module.lab1_network.private_subnet_ids[1]
  sg_kafka_id   = module.lab1_security_groups.sg_kafka_id
  sg_rabbit_id  = module.lab1_security_groups.sg_rabbit_id
  key_name      = var.lab1_key_name
  instance_type = var.instance_type_kafka
  private_ip    = var.lab1_messaging_private_ip
  tags          = var.tags
  depends_on    = [aws_route.lab1_private_to_bastion_nat]
}

locals {
  service_pairs = [
    {
      service_a = "auth"
      port_a    = 8001
      service_b = "user"
      port_b    = 8006
    },
    {
      service_a = "tutoring"
      port_a    = 8003
      service_b = "forum"
      port_b    = 8002
    },
    {
      service_a = "payment"
      port_a    = 8004
      service_b = "calendar"
      port_b    = 8005
    },
    {
      service_a = "academic-record"
      port_a    = 8007
      service_b = "notification"
      port_b    = 8008
    },
    {
      service_a = "reporting"
      port_a    = 8009
      service_b = "audit"
      port_b    = 8010
    }
  ]

  service_images = {
    auth            = "cepatino/uce_support_platform-auth-service:latest"
    user            = "cepatino/uce_support_platform-user-service:latest"
    tutoring        = "cepatino/uce_support_platform-tutoring-service:latest"
    forum           = "cepatino/uce_support_platform-forum-service:latest"
    payment         = "cepatino/uce_support_platform-payment-service:latest"
    calendar        = "cepatino/uce_support_platform-calendar-service:latest"
    "academic-record" = "cepatino/uce_support_platform-academic-record-service:latest"
    notification    = "cepatino/uce_support_platform-notification-service:latest"
    reporting       = "cepatino/uce_support_platform-reporting-service:latest"
    audit           = "cepatino/uce_support_platform-audit-service:latest"
  }

  service_base_paths = {
    auth            = "/auth"
    user            = "/users"
    tutoring        = "/tutoring"
    forum           = "/forum"
    payment         = "/payments"
    calendar        = "/calendar"
    "academic-record" = "/records"
    notification    = "/notifications"
    reporting       = "/reporting"
    audit           = "/audit"
  }
}

module "lab1_services" {
  source               = "./modules/private_ec2_services"
  providers            = { aws = aws.lab1 }
  subnet_ids           = module.lab1_network.private_subnet_ids
  sg_id                = module.lab1_security_groups.sg_services_id
  key_name             = var.lab1_key_name
  instance_type        = var.instance_type_services
  service_pairs        = local.service_pairs
  service_images       = local.service_images
  service_base_paths   = local.service_base_paths
  db_host              = module.lab1_data_stack.data_private_ip
  db_name              = var.postgres_db
  db_user              = var.postgres_user
  db_password          = var.postgres_password
  redis_host           = module.lab1_data_stack.data_private_ip
  mongo_host           = module.lab1_data_stack.data_private_ip
  kafka_bootstrap      = "${module.lab1_messaging_stack.kafka_private_ip}:9092"
  rabbitmq_host        = module.lab1_messaging_stack.rabbit_private_ip
  jwt_secret           = var.jwt_secret
  tags                 = var.tags
  depends_on           = [aws_route.lab1_private_to_bastion_nat]
}

locals {
  internal_targets = [
    { name = "auth", port = 8001, path = "/auth/*", health_path = "/auth/health", priority = 10, instance_id = module.lab1_services.instance_ids[0] },
    { name = "user", port = 8006, path = "/users/*", health_path = "/users/health", priority = 20, instance_id = module.lab1_services.instance_ids[0] },
    { name = "forum", port = 8002, path = "/forum/*", health_path = "/forum/health", priority = 30, instance_id = module.lab1_services.instance_ids[1] },
    { name = "tutoring", port = 8003, path = "/tutoring/*", health_path = "/tutoring/health", priority = 40, instance_id = module.lab1_services.instance_ids[1] },
    { name = "payment", port = 8004, path = "/payments/*", health_path = "/payments/health", priority = 50, instance_id = module.lab1_services.instance_ids[2] },
    { name = "calendar", port = 8005, path = "/calendar/*", health_path = "/calendar/health", priority = 60, instance_id = module.lab1_services.instance_ids[2] },
    { name = "academic-record", port = 8007, path = "/records/*", health_path = "/records/health", priority = 70, instance_id = module.lab1_services.instance_ids[3] },
    { name = "notification", port = 8008, path = "/notifications/*", health_path = "/notifications/health", priority = 80, instance_id = module.lab1_services.instance_ids[3] },
    { name = "reporting", port = 8009, path = "/reporting/*", health_path = "/reporting/health", priority = 90, instance_id = module.lab1_services.instance_ids[4] },
    { name = "audit", port = 8010, path = "/audit/*", health_path = "/audit/health", priority = 100, instance_id = module.lab1_services.instance_ids[4] }
  ]
}

module "lab1_internal_alb" {
  source         = "./modules/internal_alb"
  providers      = { aws = aws.lab1 }
  vpc_id         = module.lab1_network.vpc_id
  subnet_ids     = module.lab1_network.private_subnet_ids
  sg_id          = module.lab1_security_groups.sg_internal_alb_id
  targets        = local.internal_targets
  tags           = var.tags
}

module "lab1_gateway" {
  source        = "./modules/gateway_ec2"
  providers     = { aws = aws.lab1 }
  subnet_id     = module.lab1_network.public_subnet_ids[1]
  sg_id         = module.lab1_security_groups.sg_gateway_id
  key_name      = var.lab1_key_name
  instance_type = var.instance_type_gateway
  upstream_host = module.lab1_internal_alb.dns_name
  eip_allocation_id = var.lab1_gateway_eip_allocation_id
  tags          = var.tags
}

module "lab2_network" {
  source               = "./modules/network"
  providers            = { aws = aws.lab2 }
  vpc_cidr             = var.lab2_vpc_cidr
  azs                  = var.azs
  public_subnet_cidrs  = var.lab2_public_subnet_cidrs
  private_subnet_cidrs = var.lab2_private_subnet_cidrs
  enable_nat_gateway   = false
  name_prefix          = "lab2"
  tags                 = var.tags
}

module "lab2_security_groups" {
  source        = "./modules/frontend_security_groups"
  providers     = { aws = aws.lab2 }
  vpc_id        = module.lab2_network.vpc_id
  vpc_cidr      = var.lab2_vpc_cidr
  tags          = var.tags
}

locals {
  frontend_pairs = [
    {
      frontend_a = "auth"
      port_a     = 3001
      frontend_b = "user"
      port_b     = 3002
    },
    {
      frontend_a = "tutoring"
      port_a     = 3003
      frontend_b = "forum"
      port_b     = 3004
    },
    {
      frontend_a = "payment"
      port_a     = 3005
      frontend_b = "calendar"
      port_b     = 3006
    },
    {
      frontend_a = "academic-record"
      port_a     = 3007
      frontend_b = "admin"
      port_b     = 3010
    }
  ]

  frontend_images = {
    auth            = "cepatino/uce_support_platform-auth-frontend:latest"
    user            = "cepatino/uce_support_platform-user-frontend:latest"
    tutoring        = "cepatino/uce_support_platform-tutoring-frontend:latest"
    forum           = "cepatino/uce_support_platform-forum-frontend:latest"
    payment         = "cepatino/uce_support_platform-payment-frontend:latest"
    calendar        = "cepatino/uce_support_platform-calendar-frontend:latest"
    "academic-record" = "cepatino/uce_support_platform-academic-record-frontend:latest"
    admin           = "cepatino/uce_support_platform-admin-frontend:latest"
  }
}

module "lab2_frontends" {
  source        = "./modules/frontend_ec2"
  providers     = { aws = aws.lab2 }
  subnet_ids    = module.lab2_network.public_subnet_ids
  sg_id         = module.lab2_security_groups.sg_frontend_id
  key_name      = var.lab2_key_name
  instance_type = var.instance_type_frontend
  frontend_pairs = local.frontend_pairs
  frontend_images = local.frontend_images
  gateway_url   = "http://${module.lab1_gateway.eip_public_ip}"
  tags          = var.tags
}

locals {
  frontend_targets = [
    {
      name        = "auth"
      port        = 3001
      path        = "/auth/*"
      instance_id = module.lab2_frontends.instance_ids[0]
    },
    {
      name        = "user"
      port        = 3002
      path        = "/users/*"
      instance_id = module.lab2_frontends.instance_ids[0]
    },
    {
      name        = "tutoring"
      port        = 3003
      path        = "/tutoring/*"
      instance_id = module.lab2_frontends.instance_ids[1]
    },
    {
      name        = "forum"
      port        = 3004
      path        = "/forum/*"
      instance_id = module.lab2_frontends.instance_ids[1]
    },
    {
      name        = "payment"
      port        = 3005
      path        = "/payments/*"
      instance_id = module.lab2_frontends.instance_ids[2]
    },
    {
      name        = "calendar"
      port        = 3006
      path        = "/calendar/*"
      instance_id = module.lab2_frontends.instance_ids[2]
    },
    {
      name        = "academic-record"
      port        = 3007
      path        = "/records/*"
      instance_id = module.lab2_frontends.instance_ids[3]
    },
    {
      name        = "admin"
      port        = 3010
      path        = "/admin/*"
      instance_id = module.lab2_frontends.instance_ids[3]
    }
  ]
}

module "lab2_frontend_alb" {
  source     = "./modules/frontend_alb"
  providers  = { aws = aws.lab2 }
  vpc_id     = module.lab2_network.vpc_id
  subnet_ids = module.lab2_network.public_subnet_ids
  sg_id      = module.lab2_security_groups.sg_alb_id
  targets    = local.frontend_targets
  tags       = var.tags
}
