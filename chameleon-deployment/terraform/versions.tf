terraform {
  required_version = ">=1.7.2"

  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "=2.1.0"
    }

    local = {
      source  = "hashicorp/local"
      version = "2.5.0"
    }
  }
}

provider "openstack" {
  enable_logging = true
}
