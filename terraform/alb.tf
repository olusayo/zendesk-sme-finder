# Application Load Balancer Configuration

# Application Load Balancer
resource "aws_lb" "frontend" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection       = false
  enable_http2                     = true
  enable_cross_zone_load_balancing = true

  tags = merge(
    var.additional_tags,
    {
      Name = "${var.project_name}-alb"
    }
  )
}

# Target Group for ECS Service
resource "aws_lb_target_group" "frontend" {
  name        = "${var.project_name}-tg"
  port        = 8501
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/_stcore/health"
    protocol            = "HTTP"
    matcher             = "200"
  }

  deregistration_delay = 30

  tags = merge(
    var.additional_tags,
    {
      Name = "${var.project_name}-tg"
    }
  )
}

# ALB Listener (HTTP)
resource "aws_lb_listener" "frontend" {
  load_balancer_arn = aws_lb.frontend.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }

  tags = merge(
    var.additional_tags,
    {
      Name = "${var.project_name}-alb-listener"
    }
  )
}

# CloudWatch Log Group for ALB
resource "aws_cloudwatch_log_group" "alb" {
  name              = "/aws/alb/${var.project_name}"
  retention_in_days = 7

  tags = merge(
    var.additional_tags,
    {
      Name = "${var.project_name}-alb-logs"
    }
  )
}
