data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

resource "aws_instance" "this" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = [var.sg_id]
  key_name                    = var.key_name
  associate_public_ip_address = true
  source_dest_check           = false
  user_data_replace_on_change = true
  user_data                   = <<-EOF
    #!/bin/bash
    set -euxo pipefail
    exec > >(tee /var/log/user-data.log | logger -t user-data -s 2>/dev/console) 2>&1
    echo "user-data: start $(date -Is)"
    echo "user-data: version 2026-01-23-1"
    vpc_cidr="${var.vpc_cidr}"
    iface=""
    for i in $(seq 1 12); do
      iface="$(ip -o -4 route show to default | awk '{print $5}' | head -n1)"
      if [ -n "$${iface}" ]; then
        break
      fi
      sleep 5
    done
    if [ -z "$${iface}" ]; then
      iface="ens5"
    fi
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y iptables-persistent
    sysctl -w net.ipv4.ip_forward=1
    sysctl -w net.ipv4.conf.all.forwarding=1
    sysctl -w net.ipv4.conf.default.forwarding=1
    sed -i 's/^#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' /etc/sysctl.conf
    iptables -t nat -A POSTROUTING -o "$${iface}" -j MASQUERADE
    iptables -A FORWARD -s "$${vpc_cidr}" -j ACCEPT
    iptables -A FORWARD -i "$${iface}" -m state --state RELATED,ESTABLISHED -j ACCEPT
    iptables-save > /etc/iptables/rules.v4
  EOF
  tags                        = merge(var.tags, { Name = "lab1-bastion" })
}

resource "aws_eip" "this" {
  domain = "vpc"
  tags   = var.tags
}

resource "aws_eip_association" "this" {
  instance_id   = aws_instance.this.id
  allocation_id = aws_eip.this.id
}
