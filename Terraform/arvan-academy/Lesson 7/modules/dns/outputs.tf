output "a_records_id" {
  description = "The ID of A DNS records"
  value = {
    for name, record in cdn_domain_dns_record.a_records : name => record.id
  }
}
