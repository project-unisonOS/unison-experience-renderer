FROM python:3.12-slim

WORKDIR /app

# Basic tools for healthcheck and VCS installs
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir "opentelemetry-api==1.21.0" "opentelemetry-sdk==1.21.0" \
        "opentelemetry-exporter-otlp==1.21.0" "opentelemetry-exporter-jaeger==1.21.0" \
        "opentelemetry-propagator-b3==1.21.0" "opentelemetry-propagator-jaeger==1.21.0" \
        "opentelemetry-instrumentation-fastapi==0.42b0" "opentelemetry-instrumentation-httpx==0.42b0" \
    && pip install --no-cache-dir "git+https://github.com/project-unisonOS/unison-common.git@main" \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir bleach==6.3.0 jsonschema python-jose[cryptography] PyNaCl redis pytest

COPY src ./src
COPY tests ./tests

ENV PYTHONPATH=/app/src

EXPOSE 8082
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8082"]
