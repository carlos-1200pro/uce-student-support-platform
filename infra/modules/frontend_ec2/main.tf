data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

locals {
  pairs = var.frontend_pairs
}

resource "aws_instance" "frontends" {
  count                       = length(local.pairs)
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_ids[count.index % length(var.subnet_ids)]
  vpc_security_group_ids      = [var.sg_id]
  key_name                    = var.key_name
  associate_public_ip_address = true
  user_data_replace_on_change = true
  user_data = templatefile("${path.module}/user_data.sh.tmpl", {
    compose = replace(
      templatefile("${path.module}/docker-compose.yml.tmpl", {
        frontend_a_name  = local.pairs[count.index].frontend_a
        frontend_a_port  = local.pairs[count.index].port_a
        frontend_a_image = var.frontend_images[local.pairs[count.index].frontend_a]
        frontend_b_name  = local.pairs[count.index].frontend_b
        frontend_b_port  = local.pairs[count.index].port_b
        frontend_b_image = var.frontend_images[local.pairs[count.index].frontend_b]
        gateway_url      = var.gateway_url
      }),
      "$",
      "$$"
    )
  })
  tags = merge(var.tags, {
    Name = "lab2-fe-${local.pairs[count.index].frontend_a}-${local.pairs[count.index].frontend_b}"
  })
}
