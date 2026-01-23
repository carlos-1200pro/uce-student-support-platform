data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

locals {
  compose = file("${path.module}/docker-compose.yml.tmpl")
  user_data = templatefile("${path.module}/user_data.sh.tmpl", {
    compose = replace(local.compose, "$", "$$")
  })
}

resource "aws_instance" "this" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
  private_ip                  = var.private_ip
  vpc_security_group_ids      = [var.sg_kafka_id, var.sg_rabbit_id]
  key_name                    = var.key_name
  associate_public_ip_address = false
  user_data_replace_on_change = true
  user_data                   = local.user_data
  tags                        = merge(var.tags, { Name = "lab1-messaging-stack" })
}
