resource "cdn_domain_dns_record" "a_records" {
  for_each       = { for record in var.records : record.name => record if record.type == "a" }
  domain         = var.domain
  name           = each.value.name
  ttl            = each.value.ttl
  cloud          = each.value.cloud
  upstream_https = each.value.upstream_https
  ip_filter_mode = each.value.ip_filter_mode
  type           = each.value.type
  value = {
    a = [
      for a in each.value.value.a : {
        ip     = a.ip
        port   = a.port
        weight = a.weight
      }
    ]
  }
}
