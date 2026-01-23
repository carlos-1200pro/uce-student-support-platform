resource "aws_security_group" "alb" {
  name        = "frontend-alb-sg"
  description = "Public ALB for frontends"
  vpc_id      = var.vpc_id
  tags        = merge(var.tags, { Name = "lab2-sg-alb" })
}

resource "aws_security_group_rule" "alb_http" {
  type              = "ingress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  ipv6_cidr_blocks  = ["::/0"]
  security_group_id = aws_security_group.alb.id
}

resource "aws_security_group_rule" "alb_to_frontend" {
  type              = "egress"
  from_port         = 3000
  to_port           = 3100
  protocol          = "tcp"
  cidr_blocks       = [var.vpc_cidr]
  security_group_id = aws_security_group.alb.id
}

resource "aws_security_group" "frontend" {
  name        = "frontends-sg"
  description = "Frontend EC2s"
  vpc_id      = var.vpc_id
  tags        = merge(var.tags, { Name = "lab2-sg-frontends" })
}

resource "aws_security_group_rule" "frontend_from_alb" {
  type                     = "ingress"
  from_port                = 3000
  to_port                  = 3100
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb.id
  security_group_id        = aws_security_group.frontend.id
}

resource "aws_security_group_rule" "frontend_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  ipv6_cidr_blocks  = ["::/0"]
  security_group_id = aws_security_group.frontend.id
}
