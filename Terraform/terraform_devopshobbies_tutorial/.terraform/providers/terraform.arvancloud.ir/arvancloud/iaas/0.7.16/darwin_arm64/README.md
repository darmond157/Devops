# Arvan IaaS Terraform Plugin Provider

## Provider Usage

### Requirements

- [Terraform](https://www.terraform.io/downloads.html) >= 1.0
- [ArvanCloud API Key](https://panel.arvancloud.ir/profile/machine-user) with proper [Access policy](https://panel.arvancloud.ir/profile/policies)

### Getting started

Create an empty directory and put a file in it called `main.tf` that contains the following contents:

```
terraform {
  required_providers {
    arvan = {
      source = "terraform.arvancloud.ir/arvancloud/iaas"
    }
  }
}

provider "arvan" {
  api_key = "your api key"
}

variable "region" {
  type        = string
  description = "The chosen region for resources"
  default     = "ir-thr-ba1"
}

data "arvan_abraks" "instance_list" {
  region = var.region
}

output "instances" {
  value = data.arvan_abraks.instance_list.instances
}
```

Change the `api_key` to your API Key

In a terminal, go into the directory where you created `main.tf` and run the `terraform init` command:

```
terraform init
```

Now that you have the provider plugin downloaded, run the terraform apply command to see the results:

```
terraform apply
```
Type `yes` and hit Enter.

### Upgrading the provider
```
terraform init -upgrade
```

## Developing the Provider


### Requirements


- [Terraform](https://www.terraform.io/downloads.html) >= 1.0

- [Go](https://golang.org/doc/install) >= 1.19





### Building The Provider


If you wish to work on the provider, you'll first need [Go](http://www.golang.org) installed on your machine.




1. Clone the repository

1. Enter the repository directory

1. Build the provider using the Go `install` command:

To compile the provider, run `go install`. This will build the provider and put the provider binary in the `$GOPATH/bin` directory.


```shell
go install

```

To generate or update documentation, run `go generate`.



### Running the provider locally



1. Add `.terraformrc` file to your home directory

2. Add the following content to `.terraformrc`

```
provider_installation {
 dev_overrides {
   "terraform.arvancloud.ir/arvancloud/iaas" = "/path/to/your/go/bin"
 }
 direct {}
}
```

