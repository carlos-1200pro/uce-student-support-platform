output "private_ips" {
  value = [for i in aws_instance.services : i.private_ip]
}

output "instance_ids" {
  value = [for i in aws_instance.services : i.id]
}
