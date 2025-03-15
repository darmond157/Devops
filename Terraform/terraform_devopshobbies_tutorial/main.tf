resource "aws_instance" "bardia" {
  ami           = var.ami_id
  instance_type = var.instance_type
  key_name      = var.key_name

  tags = {
    Name       = var.machine_name
    Created_By = "terraform"
  }
}