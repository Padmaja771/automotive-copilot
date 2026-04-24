terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "copilot_rg" {
  name     = "${var.project_name}-rg-${var.environment}"
  location = var.azure_region
}

# ============================================================
# Azure Blob Storage (Equivalent to AWS S3)
# ============================================================
resource "azurerm_storage_account" "vehicle_docs_sa" {
  # Azure storage names must be globally unique, lowercase, and no dashes
  name                     = replace("${var.project_name}docs${var.environment}", "-", "")
  resource_group_name      = azurerm_resource_group.copilot_rg.name
  location                 = azurerm_resource_group.copilot_rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
}

resource "azurerm_storage_container" "incoming_docs" {
  name                  = "incoming"
  storage_account_name  = azurerm_storage_account.vehicle_docs_sa.name
  container_access_type = "private"
}

# ============================================================
# Azure Data Factory (Equivalent to AWS Lambda orchestration)
# ============================================================
resource "azurerm_data_factory" "copilot_adf" {
  name                = "${var.project_name}-adf-${var.environment}"
  resource_group_name = azurerm_resource_group.copilot_rg.name
  location            = azurerm_resource_group.copilot_rg.location

  identity {
    type = "SystemAssigned"
  }
}

# Grant ADF permission to read the Blob Storage
resource "azurerm_role_assignment" "adf_blob_reader" {
  scope                = azurerm_storage_account.vehicle_docs_sa.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_data_factory.copilot_adf.identity[0].principal_id
}

output "azure_storage_account_name" {
  value = azurerm_storage_account.vehicle_docs_sa.name
}

output "azure_data_factory_name" {
  value = azurerm_data_factory.copilot_adf.name
}
