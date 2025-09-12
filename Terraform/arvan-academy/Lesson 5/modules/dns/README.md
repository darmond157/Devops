# DNS Records

This module creates DNS records in ArvanCloud CDN

## Requirements

| Name                              | Version  |
| --------------------------------- | -------- |
| [terraform](https://terraform.io) | >= 1.9.0 |

## Providers

| Name                                                               | Version  |
| ------------------------------------------------------------------ | -------- |
| [CDN](https://git.arvancloud.ir/arvancloud/cdn/terraform-provider) | >= 1.0.0 |

## Resources

| Name                                                                                                                                                      | Type     |
| --------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| [cdn_domain_dns_record](https://git.arvancloud.ir/arvancloud/cdn/terraform-provider/-/blob/main/internal/resources/dns_record_resource.go?ref_type=heads) | resource |

## Inputs

| Name        | Description     | Type     | Default | Required |
| ----------- | --------------- | -------- | ------- | :------: |
| domain      | The domain name | `string` | n/a     |   yes    |
| record_name | The record name | `string` | n/a     |   yes    |

## Outputs

| Name         | Description            |
| ------------ | ---------------------- |
| a_records_id | The ID of the A record |
