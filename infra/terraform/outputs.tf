output "ec2_public_ips" {
  value = var.instance_count == 1 ? [aws_instance.single[0].public_ip] : []
}

output "alb_dns" {
  value = var.instance_count > 1 ? aws_lb.alb[0].dns_name : "No ALB"
}
