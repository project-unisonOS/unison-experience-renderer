FROM python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de AS common_wheel

ARG UNISON_COMMON_REF="45a261eb1442454c4541b75dcb6f43b8bb32027f"
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip wheel --no-cache-dir --no-deps --wheel-dir /tmp/wheels \
       "git+https://github.com/project-unisonOS/unison-common.git@${UNISON_COMMON_REF}"
FROM python:3.12-slim@sha256:fdab368dc2e04fab3180d04508b41732756cc442586f708021560ee1341f3d29

ARG REPO_PATH="."
ARG GIT_SHA="unknown"
ARG BUILD_TIME="unknown"
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY ${REPO_PATH}/constraints.txt ./constraints.txt
COPY ${REPO_PATH}/requirements.txt ./requirements.txt
COPY --from=common_wheel /tmp/wheels /tmp/wheels
RUN pip install --no-cache-dir "setuptools<81" \
    && pip install --no-cache-dir -c ./constraints.txt /tmp/wheels/unison_common-*.whl \
    && pip install --no-cache-dir -c ./constraints.txt -r requirements.txt

COPY ${REPO_PATH}/src/ ./src/
COPY ${REPO_PATH}/tests ./tests

LABEL org.opencontainers.image.revision="${GIT_SHA}"
LABEL org.opencontainers.image.created="${BUILD_TIME}"

ENV UNISON_RENDERER_BUILD_SHA="${GIT_SHA}"
ENV UNISON_RENDERER_BUILD_TIME="${BUILD_TIME}"
ENV PYTHONPATH=/app/src
EXPOSE 8082
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8082"]
