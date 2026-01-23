output "bastion_eip" {
  value = module.lab1_bastion.eip_public_ip
}

output "gateway_eip" {
  value = module.lab1_gateway.eip_public_ip
}

output "lb_microservices_dns" {
  value = module.lab1_internal_alb.dns_name
}

output "lb_frontend_dns" {
  value = module.lab2_frontend_alb.dns_name
}
