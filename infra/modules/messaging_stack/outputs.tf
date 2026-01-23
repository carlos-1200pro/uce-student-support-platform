output "private_ip" {
  value = aws_instance.this.private_ip
}

output "kafka_private_ip" {
  value = aws_instance.this.private_ip
}

output "rabbit_private_ip" {
  value = aws_instance.this.private_ip
}
