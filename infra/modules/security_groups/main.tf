locals {
  is_ipv6 = can(regex(":", var.my_ip_cidr))
  ssh_ipv4 = local.is_ipv6 ? [] : [var.my_ip_cidr]
  ssh_ipv6 = local.is_ipv6 ? [var.my_ip_cidr] : []
}

resource "aws_security_group" "gateway" {
  name        = "gateway-sg"
  description = "Public API Gateway"
  vpc_id      = var.vpc_id
  tags        = merge(var.tags, { Name = "lab1-sg-gateway" })
}

resource "aws_security_group_rule" "gateway_http" {
  type              = "ingress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  ipv6_cidr_blocks  = ["::/0"]
  security_group_id = aws_security_group.gateway.id
}

resource "aws_security_group_rule" "gateway_https" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  ipv6_cidr_blocks  = ["::/0"]
  security_group_id = aws_security_group.gateway.id
}

resource "aws_security_group_rule" "gateway_to_internal_alb" {
  type              = "egress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = [var.vpc_cidr]
  security_group_id = aws_security_group.gateway.id
}

resource "aws_security_group_rule" "gateway_egress_https" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  ipv6_cidr_blocks  = ["::/0"]
  security_group_id = aws_security_group.gateway.id
}

resource "aws_security_group_rule" "gateway_egress_http" {
  type              = "egress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  ipv6_cidr_blocks  = ["::/0"]
  security_group_id = aws_security_group.gateway.id
}
resource "aws_security_group" "internal_alb" {
  name        = "internal-alb-sg"
  description = "Internal ALB"
  vpc_id      = var.vpc_id
  tags        = merge(var.tags, { Name = "lab1-sg-internal-alb" })
}

resource "aws_security_group_rule" "internal_alb_from_gateway" {
  type                     = "ingress"
  from_port                = 80
  to_port                  = 80
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.gateway.id
  security_group_id        = aws_security_group.internal_alb.id
}

resource "aws_security_group_rule" "internal_alb_to_services" {
  for_each          = toset([for p in var.microservice_ports : tostring(p)])
  type              = "egress"
  from_port         = tonumber(each.value)
  to_port           = tonumber(each.value)
  protocol          = "tcp"
  cidr_blocks       = [var.vpc_cidr]
  security_group_id = aws_security_group.internal_alb.id
}

resource "aws_security_group" "bastion" {
  name        = "bastion-sg"
  description = "Bastion Host"
  vpc_id      = var.vpc_id
  tags        = merge(var.tags, { Name = "lab1-sg-bastion" })
}

resource "aws_security_group_rule" "bastion_ssh_in" {
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = local.ssh_ipv4
  ipv6_cidr_blocks  = local.ssh_ipv6
  security_group_id = aws_security_group.bastion.id
}

resource "aws_security_group_rule" "bastion_from_private" {
  type              = "ingress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = [var.vpc_cidr]
  security_group_id = aws_security_group.bastion.id
}

resource "aws_security_group_rule" "bastion_ssh_out" {
  type              = "egress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = [var.vpc_cidr]
  security_group_id = aws_security_group.bastion.id
}

resource "aws_security_group_rule" "bastion_egress_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  ipv6_cidr_blocks  = ["::/0"]
  security_group_id = aws_security_group.bastion.id
}

resource "aws_security_group" "services" {
  name        = "services-sg"
  description = "Private microservices"
  vpc_id      = var.vpc_id
  tags        = merge(var.tags, { Name = "lab1-sg-services" })
}

resource "aws_security_group_rule" "services_from_internal_alb" {
  for_each                 = toset([for p in var.microservice_ports : tostring(p)])
  type                     = "ingress"
  from_port                = tonumber(each.value)
  to_port                  = tonumber(each.value)
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.internal_alb.id
  security_group_id        = aws_security_group.services.id
}

resource "aws_security_group_rule" "services_ssh_from_bastion" {
  type                     = "ingress"
  from_port                = 22
  to_port                  = 22
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.bastion.id
  security_group_id        = aws_security_group.services.id
}

resource "aws_security_group_rule" "services_to_data" {
  for_each          = toset([for p in [5432, 6379, 27017, 9092, 5672] : tostring(p)])
  type              = "egress"
  from_port         = tonumber(each.value)
  to_port           = tonumber(each.value)
  protocol          = "tcp"
  cidr_blocks       = [var.vpc_cidr]
  security_group_id = aws_security_group.services.id
}

resource "aws_security_group_rule" "services_egress_https" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  ipv6_cidr_blocks  = ["::/0"]
  security_group_id = aws_security_group.services.id
}

resource "aws_security_group_rule" "services_egress_http" {
  type              = "egress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  ipv6_cidr_blocks  = ["::/0"]
  security_group_id = aws_security_group.services.id
}

resource "aws_security_group" "db" {
  name        = "db-sg"
  description = "Postgres"
  vpc_id      = var.vpc_id
  tags        = merge(var.tags, { Name = "lab1-sg-db" })
}

resource "aws_security_group_rule" "db_ssh_from_bastion" {
  type                     = "ingress"
  from_port                = 22
  to_port                  = 22
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.bastion.id
  security_group_id        = aws_security_group.db.id
}

resource "aws_security_group_rule" "db_from_services" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.services.id
  security_group_id        = aws_security_group.db.id
}

resource "aws_security_group_rule" "db_egress_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  ipv6_cidr_blocks  = ["::/0"]
  security_group_id = aws_security_group.db.id
}

resource "aws_security_group" "redis" {
  name        = "redis-sg"
  description = "Redis"
  vpc_id      = var.vpc_id
  tags        = merge(var.tags, { Name = "lab1-sg-redis" })
}

resource "aws_security_group_rule" "redis_ssh_from_bastion" {
  type                     = "ingress"
  from_port                = 22
  to_port                  = 22
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.bastion.id
  security_group_id        = aws_security_group.redis.id
}

resource "aws_security_group_rule" "redis_from_services" {
  type                     = "ingress"
  from_port                = 6379
  to_port                  = 6379
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.services.id
  security_group_id        = aws_security_group.redis.id
}

resource "aws_security_group_rule" "redis_egress_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  ipv6_cidr_blocks  = ["::/0"]
  security_group_id = aws_security_group.redis.id
}

resource "aws_security_group" "mongo" {
  name        = "mongo-sg"
  description = "MongoDB"
  vpc_id      = var.vpc_id
  tags        = merge(var.tags, { Name = "lab1-sg-mongo" })
}

resource "aws_security_group_rule" "mongo_ssh_from_bastion" {
  type                     = "ingress"
  from_port                = 22
  to_port                  = 22
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.bastion.id
  security_group_id        = aws_security_group.mongo.id
}

resource "aws_security_group_rule" "mongo_from_services" {
  type                     = "ingress"
  from_port                = 27017
  to_port                  = 27017
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.services.id
  security_group_id        = aws_security_group.mongo.id
}

resource "aws_security_group_rule" "mongo_egress_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  ipv6_cidr_blocks  = ["::/0"]
  security_group_id = aws_security_group.mongo.id
}

resource "aws_security_group" "kafka" {
  name        = "kafka-sg"
  description = "Kafka"
  vpc_id      = var.vpc_id
  tags        = merge(var.tags, { Name = "lab1-sg-kafka" })
}

resource "aws_security_group_rule" "kafka_ssh_from_bastion" {
  type                     = "ingress"
  from_port                = 22
  to_port                  = 22
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.bastion.id
  security_group_id        = aws_security_group.kafka.id
}

resource "aws_security_group_rule" "kafka_from_services" {
  type                     = "ingress"
  from_port                = 9092
  to_port                  = 9092
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.services.id
  security_group_id        = aws_security_group.kafka.id
}

resource "aws_security_group_rule" "kafka_egress_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  ipv6_cidr_blocks  = ["::/0"]
  security_group_id = aws_security_group.kafka.id
}

resource "aws_security_group" "rabbit" {
  name        = "rabbit-sg"
  description = "RabbitMQ"
  vpc_id      = var.vpc_id
  tags        = merge(var.tags, { Name = "lab1-sg-rabbit" })
}

resource "aws_security_group_rule" "rabbit_ssh_from_bastion" {
  type                     = "ingress"
  from_port                = 22
  to_port                  = 22
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.bastion.id
  security_group_id        = aws_security_group.rabbit.id
}

resource "aws_security_group_rule" "rabbit_from_services" {
  type                     = "ingress"
  from_port                = 5672
  to_port                  = 5672
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.services.id
  security_group_id        = aws_security_group.rabbit.id
}

resource "aws_security_group_rule" "rabbit_egress_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  ipv6_cidr_blocks  = ["::/0"]
  security_group_id = aws_security_group.rabbit.id
}
