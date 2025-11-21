FROM python:3.12-slim

WORKDIR /app

# Basic tools for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY unison-common/dist /unison-common/dist
COPY unison-experience-renderer/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --no-deps /unison-common/dist/unison_common-0.1.0-py3-none-any.whl \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir bleach==6.3.0 jsonschema python-jose[cryptography] PyNaCl redis \
        opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp opentelemetry-exporter-jaeger \
        opentelemetry-propagator-b3 opentelemetry-propagator-jaeger opentelemetry-instrumentation-fastapi \
        opentelemetry-instrumentation-httpx

COPY unison-experience-renderer/src ./src
COPY unison-common/src/unison_common ./src/unison_common

ENV PYTHONPATH=/app/src

EXPOSE 8082
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8082"]
