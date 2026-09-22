resource "aws_security_group" "alb" {
  name        = "${var.name_prefix}-alb"
  description = "Public HTTP access to the RoundReady frontend ALB"
  vpc_id      = var.vpc_id
  ingress {
    description = "Public HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    description     = "ALB to private K3s nodes"
    from_port       = var.target_port
    to_port         = var.target_port
    protocol        = "tcp"
    security_groups = [var.k3s_node_security_group_id]
  }
  tags = merge(var.common_tags, { Name = "${var.name_prefix}-alb" })
}

resource "aws_lb" "this" {
  name               = "${var.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  ip_address_type    = "ipv4"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids
  tags               = merge(var.common_tags, { Name = "${var.name_prefix}-alb" })
}

resource "aws_lb_target_group" "frontend" {
  name        = "${var.name_prefix}-frontend"
  port        = var.target_port
  protocol    = "HTTP"
  target_type = "instance"
  vpc_id      = var.vpc_id
  health_check {
    enabled             = true
    path                = var.health_check_path
    protocol            = "HTTP"
    port                = "traffic-port"
    matcher             = "200-399"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
  tags = merge(var.common_tags, { Name = "${var.name_prefix}-frontend-targets" })
}

resource "aws_lb_target_group_attachment" "frontend" {
  for_each = {
    server = var.k3s_instance_ids[0]
    worker = var.k3s_instance_ids[1]
  }
  target_group_arn = aws_lb_target_group.frontend.arn
  target_id        = each.value
  port             = var.target_port
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

resource "aws_vpc_security_group_ingress_rule" "k3s_from_alb" {
  security_group_id            = var.k3s_node_security_group_id
  referenced_security_group_id = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = var.target_port
  to_port                      = var.target_port
  description                  = "Frontend NodePort from the RoundReady ALB"
}
