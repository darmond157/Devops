terraform {
  required_providers {
    arvan = {
      source = "terraform.arvancloud.ir/arvancloud/iaas"
    }
  }
}

provider "arvan" {
  api_key = "apikey c369df69-bc42-545e-beb0-c909d7578dfb"
}

variable "region" {
  type        = string
  description = "The chosen region for resources"
  default     = "ir-thr-ba1"
}

data "arvan_images" "image_list" {
  region     = var.region
  image_type = "distributions"
}

output "images" {
  value = data.arvan_images.image_list.distributions
}