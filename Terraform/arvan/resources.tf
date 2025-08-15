# resource "arvan_security_group" "terraform_security_group" {
#   region      = var.region
#   description = "Terraform-created security group"
#   name        = "lesson_1"
#   rules = [
#     { direction = "ingress", protocol = "icmp" },
#     { direction = "ingress", protocol = "udp" },
#     { direction = "ingress", protocol = "tcp" },
#     { direction = "egress", protocol = "" }
#   ]
# }

# resource "arvan_volume" "terraform_volume" {
#   region      = var.region
#   description = "Terraform-created volume"
#   name        = "lesson_1"
#   size        = 10
# }

# resource "arvan_network" "terraform_private_network" {
#   region         = var.region
#   description    = "Terraform-created private network"
#   name           = "lesson_1"
#   dhcp_range     = { start = "10.255.255.19", end = "10.255.255.150" }
#   dns_servers    = ["8.8.8.8", "1.1.1.1"]
#   enable_dhcp    = true
#   enable_gateway = true
#   cidr           = "10.255.255.0/24"
#   gateway_ip     = "10.255.255.1"
# }

# resource "arvan_abrak" "lesson_1" {
#   depends_on = [arvan_volume.terraform_volume, arvan_network.terraform_private_network, arvan_security_group.terraform_security_group]
#   timeouts {
#     create = "1h30m"
#     update = "2h"
#     delete = "20m"
#     read   = "10m"
#   }
#   region          = var.region
#   name            = "lesson_1"
#   count           = 1
#   image_id        = local.chosen_image[0].id
#   flavor_id       = local.selected_plan.id
#   disk_size       = 25
#   server_group_id = var.chosen_server_group_id
#   networks        = [{ network_id = arvan_network.terraform_private_network.network_id }]
#   security_groups = [arvan_security_group.terraform_security_group.id]
#   volumes         = [arvan_volume.terraform_volume.id]
# }
