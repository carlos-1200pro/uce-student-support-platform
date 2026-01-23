output "public_ip" {
  value = aws_instance.this.public_ip
}

output "eip_public_ip" {
  value = length(aws_eip.this) > 0 ? aws_eip.this[0].public_ip : data.aws_eip.existing[0].public_ip
}
