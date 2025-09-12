module "dns" {
  source = "./modules/dns"
  domain = "r1c-academy.ir"
  records = [
    {
      name           = "api"
      ttl            = 3600
      cloud          = true
      upstream_https = "https"
      ip_filter_mode = {
        count      = "single"
        order      = "none"
        geo_filter = "none"
      }
      type = "a"
      value = {
        a = [
          {
            ip   = "1.2.3.4"
            port = 443
          },
          {
            ip     = "1.2.3.5"
            weight = 443
          },
        ]
      }
    },
    {
      name           = "assets"
      ttl            = 3600
      cloud          = true
      upstream_https = "https"
      ip_filter_mode = {
        count      = "single"
        order      = "none"
        geo_filter = "none"
      }
      type = "a"
      value = {
        a = [
          {
            ip   = "5.6.7.8"
            port = 443
          }
        ]
      }
    },
  ]
}
