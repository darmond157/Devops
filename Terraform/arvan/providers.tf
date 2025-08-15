terraform {
  required_providers {
    arvan = {
      source  = "terraform.arvancloud.ir/arvancloud/iaas"
      version = "0.8.1"
    }
  }
}

provider "arvan" {
  api_key = "apikey 529650df-627e-55f4-bd66-bae4feb34299"
}
