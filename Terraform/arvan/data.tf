data "arvan_images" "terraform_image" {
  region     = var.region
  image_type = "distributions"
}

data "arvan_plans" "plan_list" {
  region = var.region
}

data "arvan_server_groups" "server_group_list" {
  region = var.region
}

data "arvan_dedicated_servers" "terraform_dedicated_server" {
  region = var.region
}

data "arvan_networks" "terraform_network" {
  region = var.region
}
