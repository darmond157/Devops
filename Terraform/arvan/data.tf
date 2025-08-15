data "arvan_images" "terraform_image" {
  region     = var.region
  image_type = "distributions"
}

data "arvan_plans" "plan_list" {
  region = var.region
}

data "arvan_networks" "terraform_network" {
  region = var.region
}

data "arvan_security_groups" "default_security_groups" {
  region = var.region
}
