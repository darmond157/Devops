resource "azurerm_resource_group" "example" {
  name     = "example"
  location = "East US"

  lifecycle {
    create_before_destroy = true
  }
}

resource "azurerm_virtual_network" "example" {
  name                = "vnet"
  address_space       = ["10.0.0.0/12"]
  location            = "East US"
  resource_group_name = azurerm_resource_group.example.name

  tags = {
    Environment = "Production"
    Department  = "IT"
    Project     = "CDN"
  }

  lifecycle {
    ignore_changes = [
      tags,
    ]
  }
}

resource "azurerm_storage_account" "example" {
  name                     = "example"
  resource_group_name      = azurerm_resource_group.example.name
  location                 = "East US"
  account_tier             = "Standard"
  account_replication_type = "LRS"

  lifecycle {
    ignore_changes = all
  }
}

