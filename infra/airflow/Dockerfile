FROM apache/airflow:2.9.3-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*
USER airflow

ENV AIRFLOW_HOME=/opt/airflow
ENV PYTHONPATH=/opt/nilrag:${PYTHONPATH}
WORKDIR /opt/nilrag

# Install backend/ingestion dependencies used by the DAGs.
COPY requirements.txt /opt/nilrag/requirements.txt
RUN pip install --no-cache-dir -r /opt/nilrag/requirements.txt

# The repo itself is bind-mounted at runtime via docker compose to /opt/nilrag
# so no further COPY is required here.
