# Example Terraform configuration for Infrash
# This demonstrates how to create basic AWS resources

provider "aws" {
  region = var.aws_region
}

resource "aws_instance" "infrash_server" {
  ami           = var.ami_id
  instance_type = "t2.micro"
  
  tags = {
    Name = "infrash-server"
    Environment = var.environment
    ManagedBy = "infrash"
  }
}

resource "aws_s3_bucket" "infrash_data" {
  bucket = "infrash-data-${var.environment}"
  
  tags = {
    Name = "infrash-data"
    Environment = var.environment
    ManagedBy = "infrash"
  }
}

output "server_ip" {
  value = aws_instance.infrash_server.public_ip
}
