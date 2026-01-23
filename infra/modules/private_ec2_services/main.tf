data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

locals {
  pairs = var.service_pairs
}

resource "aws_instance" "services" {
  count                       = length(local.pairs)
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_ids[count.index % length(var.subnet_ids)]
  vpc_security_group_ids      = [var.sg_id]
  key_name                    = var.key_name
  associate_public_ip_address = false
  user_data_replace_on_change = true
  user_data = templatefile("${path.module}/user_data.sh.tmpl", {
    compose = replace(
      templatefile("${path.module}/docker-compose.yml.tmpl", {
        service_a_name  = local.pairs[count.index].service_a
        service_a_port  = local.pairs[count.index].port_a
        service_a_image = var.service_images[local.pairs[count.index].service_a]
        service_a_base_path = var.service_base_paths[local.pairs[count.index].service_a]
        service_b_name  = local.pairs[count.index].service_b
        service_b_port  = local.pairs[count.index].port_b
        service_b_image = var.service_images[local.pairs[count.index].service_b]
        service_b_base_path = var.service_base_paths[local.pairs[count.index].service_b]
        db_host         = var.db_host
        db_name         = var.db_name
        db_user         = var.db_user
        db_password     = var.db_password
        redis_host      = var.redis_host
        mongo_host      = var.mongo_host
        kafka_bootstrap = var.kafka_bootstrap
        rabbitmq_host   = var.rabbitmq_host
        jwt_secret      = var.jwt_secret
      }),
      "$",
      "$$"
    )
  })
  tags = merge(var.tags, {
    Name = "lab1-ms-${local.pairs[count.index].service_a}-${local.pairs[count.index].service_b}"
  })
}
