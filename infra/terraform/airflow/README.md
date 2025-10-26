# Airflow Pools & Queues (Terraform)

This module manages Airflow pools/queues through a ConfigMap that the Helm chart/table is configured to consume. Usage:

```bash
cd infra/terraform/airflow
terraform init
terraform apply \
  -var "kubernetes_host=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')" \
  -var "kubernetes_token=$(kubectl get secret airflow-sa -n airflow -o jsonpath='{.data.token}' | base64 --decode)" \
  -var "kubernetes_ca=$(kubectl config view --raw --minify -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')"
```

Customize `airflow_pools` / `airflow_queues` variables to enforce Reddit / LLM concurrency. The emitted ConfigMaps can be mounted and referenced by the official Airflow chart (e.g., via `extraConfigMaps`).

Secrets automation pairs with `scripts/render-secrets.sh`, which renders template YAML credentials under `SECRETS_DIR` (see infra/secrets/README.md) and feeds the file paths into `.env` for GraphQL + Airflow containers.
