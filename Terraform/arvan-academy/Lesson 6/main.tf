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

resource "cdn_domain_dns_record" "monitoring_record" {
  cloud          = true
  domain         = "r1c-academy.ir"
  name           = "monitoring"
  ttl            = 3600
  type           = "a"
  upstream_https = "https"
  ip_filter_mode = {
    count      = "single"
    order      = "none"
    geo_filter = "none"
  }
  value = {
    a = [
      {
        ip   = "5.6.7.8"
        port = 80
      },
    ]
  }
}
