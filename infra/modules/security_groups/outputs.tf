output "sg_gateway_id" {
  value = aws_security_group.gateway.id
}

output "sg_internal_alb_id" {
  value = aws_security_group.internal_alb.id
}

output "sg_bastion_id" {
  value = aws_security_group.bastion.id
}

output "sg_services_id" {
  value = aws_security_group.services.id
}

output "sg_db_id" {
  value = aws_security_group.db.id
}

output "sg_redis_id" {
  value = aws_security_group.redis.id
}

output "sg_mongo_id" {
  value = aws_security_group.mongo.id
}

output "sg_kafka_id" {
  value = aws_security_group.kafka.id
}

output "sg_rabbit_id" {
  value = aws_security_group.rabbit.id
}
