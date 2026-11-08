terraform {
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "3.2.4"
    }
  }
}

resource "null_resource" "demo" {}

output "demo_id" {
  value = null_resource.demo.id
}
