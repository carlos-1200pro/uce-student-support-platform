resource "aws_lb" "this" {
  name               = "public-frontends-alb"
  internal           = false
  load_balancer_type = "application"
  subnets            = var.subnet_ids
  security_groups    = [var.sg_id]
  tags               = merge(var.tags, { Name = "lab2-frontend-alb" })
}

resource "aws_lb_target_group" "fe" {
  for_each = { for t in var.targets : t.name => t }

  name        = "tg-fe-${each.key}"
  port        = each.value.port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "instance"

  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 2
    interval            = 30
    timeout             = 5
    matcher             = "200-399"
  }

  tags = merge(var.tags, { Name = "lab2-tg-${each.key}" })
}

resource "aws_lb_target_group_attachment" "fe_attach" {
  for_each         = { for t in var.targets : t.name => t }
  target_group_arn = aws_lb_target_group.fe[each.key].arn
  target_id        = each.value.instance_id
  port             = each.value.port
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.fe[var.targets[0].name].arn
  }
}

resource "aws_lb_listener_rule" "paths" {
  for_each     = { for t in var.targets : t.name => t if t.name != var.targets[0].name }
  listener_arn = aws_lb_listener.http.arn
  priority     = each.key == "user" ? 10 : each.key == "tutoring" ? 20 : each.key == "forum" ? 30 : each.key == "payment" ? 40 : each.key == "calendar" ? 50 : each.key == "academic-record" ? 60 : 70

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.fe[each.key].arn
  }

  condition {
    path_pattern {
      values = [each.value.path]
    }
  }
}
