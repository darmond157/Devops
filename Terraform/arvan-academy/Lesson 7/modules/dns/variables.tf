variable "domain" {
  description = "The domain name for the DNS zone"
  type        = string
}

variable "records" {
  description = "The list of DNS records"
  type = list(object({
    name           = string
    ttl            = number
    cloud          = bool
    upstream_https = string
    ip_filter_mode = object({
      count      = string
      order      = string
      geo_filter = string
    })
    type = string
    value = object({
      a = optional(list(object({
        ip      = string
        country = optional(string)
        port    = optional(number)
        weight  = optional(number)
      })))
    })
  }))

  validation {
    condition     = length(var.records) > 0
    error_message = "The records list must contain at least one record"
  }

}
