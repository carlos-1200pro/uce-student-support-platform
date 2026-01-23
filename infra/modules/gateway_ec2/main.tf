data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

locals {
  nginx_conf = templatefile("${path.module}/nginx.conf.tmpl", {
    upstream_host = var.upstream_host
  })
  compose = file("${path.module}/docker-compose.yml.tmpl")
  user_data = templatefile("${path.module}/user_data.sh.tmpl", {
    nginx_conf = local.nginx_conf
    compose    = replace(local.compose, "$", "$$")
  })
}

resource "aws_instance" "this" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = [var.sg_id]
  key_name                    = var.key_name
  associate_public_ip_address = true
  user_data_replace_on_change = true
  user_data                   = local.user_data
  tags                        = merge(var.tags, { Name = "lab1-api-gateway" })
}

data "aws_eip" "existing" {
  count         = var.eip_allocation_id == "" ? 0 : 1
  id            = var.eip_allocation_id
}

resource "aws_eip" "this" {
  count  = var.eip_allocation_id == "" ? 1 : 0
  domain = "vpc"
  tags   = var.tags
}

resource "aws_eip_association" "this" {
  instance_id   = aws_instance.this.id
  allocation_id = var.eip_allocation_id == "" ? aws_eip.this[0].id : var.eip_allocation_id
}
