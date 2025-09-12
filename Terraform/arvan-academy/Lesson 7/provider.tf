terraform {
  required_providers {
    cdn = {
      source = "terraform.arvancloud.ir/arvancloud/cdn"
    }
  }
}

provider "cdn" {
  apikey = ""
}
