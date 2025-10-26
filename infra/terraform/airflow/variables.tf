variable "kubernetes_host" {
  type        = string
  description = "Kubernetes API server for the Airflow namespace"
}

variable "kubernetes_token" {
  type        = string
  description = "Service account token with access to the Airflow namespace"
  sensitive   = true
}

variable "kubernetes_ca" {
  type        = string
  description = "Base64 encoded cluster CA certificate"
  default     = null
}

variable "airflow_namespace" {
  type        = string
  default     = "airflow"
  description = "Namespace where Airflow is deployed"
}

variable "airflow_pools" {
  type = list(object({
    name        = string
    description = optional(string, "")
    slots       = number
  }))
  default = [
    {
      name  = "reddit_api"
      slots = 8
    },
    {
      name  = "llm_enrichment"
      slots = 4
    }
  ]
  description = "Airflow pools to enforce rate limits"
}

variable "airflow_queues" {
  type = list(object({
    name        = string
    concurrency = number
    description = optional(string, "")
  }))
  default = [
    {
      name        = "reddit_ingest"
      concurrency = 2
    },
    {
      name        = "analysis_enrich"
      concurrency = 1
    }
  ]
  description = "Queue metadata surfaced to workers (referenced in DAG definitions)."
}
