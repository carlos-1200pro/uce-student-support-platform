output "eip_public_ip" {
  value = aws_eip.nat.public_ip
}
