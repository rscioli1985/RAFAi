terraform {
  required_version = ">= 1.5.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.25"
    }
  }
}

provider "kubernetes" {
  host                   = var.kubernetes_host
  token                  = var.kubernetes_token
  cluster_ca_certificate = var.kubernetes_ca
}

locals {
  pools = { for pool in var.airflow_pools : pool.name => pool }
  queues = { for queue in var.airflow_queues : queue.name => queue }
}

resource "kubernetes_config_map" "airflow_pools" {
  metadata {
    name      = "custom-airflow-pools"
    namespace = var.airflow_namespace
    labels = {
      "managed-by" = "terraform"
    }
  }
  data = {
    "pools.yaml" = yamlencode({
      pools = [
        for pool in var.airflow_pools : {
          name        = pool.name
          description = pool.description
          slots       = pool.slots
        }
      ]
    })
  }
}

resource "kubernetes_config_map" "airflow_variables" {
  metadata {
    name      = "custom-airflow-queues"
    namespace = var.airflow_namespace
  }

  data = {
    "queues.json" = jsonencode({
      queues = [
        for queue in var.airflow_queues : {
          name        = queue.name
          concurrency = queue.concurrency
          description = queue.description
        }
      ]
    })
  }
}

output "pools_config_map" {
  value = kubernetes_config_map.airflow_pools.metadata[0].name
}

output "queues_config_map" {
  value = kubernetes_config_map.airflow_variables.metadata[0].name
}
