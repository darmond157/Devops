terraform {
  backend "s3" {
    endpoints = {
      s3 = "https://s3.ir-thr-at1.arvanstorage.ir"
    }
    bucket                      = "academy-terraform"
    key                         = "terraform.tfstate"
    access_key                  = "<your_access_key>"
    secret_key                  = "<your_secret_key>"
    region                      = "ir-thr-at1"
    skip_region_validation      = true
    skip_credentials_validation = true
    skip_requesting_account_id  = true
    skip_metadata_api_check     = true
    skip_s3_checksum            = true
    encrypt                     = false
  }
}

// -----------------------------------------------------------

terraform {
  backend "pg" {
    conn_str = "postgres://user:pass@db.r1c-academy.ir/terraform_backend"
  }
}
