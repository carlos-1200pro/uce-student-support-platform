# ===============================
# VPC
# ===============================
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  tags = {
    Name = "${var.service_name}-vpc"
  }
}

# ===============================
# Subnet
# ===============================
resource "aws_subnet" "main" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-1a"
  tags = {
    Name = "${var.service_name}-subnet"
  }
}

# ===============================
# Security Group
# ===============================
resource "aws_security_group" "ec2_sg" {
  name        = "${var.service_name}-sg"
  description = "Allow HTTP, HTTPS, SSH"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ===============================
# Launch Template (EC2)
# ===============================
resource "aws_launch_template" "lt" {
  name_prefix   = "${var.service_name}-lt"
  image_id      = "ami-0c94855ba95c71c99" # Cambiar según región
  instance_type = "t2.micro"

  network_interfaces {
    associate_public_ip_address = true
    security_groups             = [aws_security_group.ec2_sg.id]
  }
}

# ===============================
# EC2 Instances para laboratorios con solo 1 instancia (lab-gateway)
# ===============================
resource "aws_instance" "single" {
  count         = var.instance_count == 1 ? 1 : 0
  ami           = "ami-0c94855ba95c71c99"
  instance_type = "t2.micro"
  subnet_id     = aws_subnet.main.id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]
  tags = {
    Name = "${var.service_name}-instance"
  }
}

# ===============================
# ALB y Auto Scaling Group solo para laboratorios con instance_count > 1
# ===============================
resource "aws_lb" "alb" {
  count               = var.instance_count > 1 ? 1 : 0
  name                = "${var.service_name}-alb"
  internal            = false
  load_balancer_type  = "application"
  security_groups     = [aws_security_group.ec2_sg.id]
  subnets             = [aws_subnet.main.id]
}

resource "aws_autoscaling_group" "asg" {
  count               = var.instance_count > 1 ? 1 : 0
  desired_capacity    = var.instance_count
  max_size            = var.instance_count
  min_size            = var.instance_count
  launch_template {
    id      = aws_launch_template.lt.id
    version = "$Latest"
  }
  vpc_zone_identifier = [aws_subnet.main.id]
}
