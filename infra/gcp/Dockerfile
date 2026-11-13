# Experiment 2 job image: Ollama (the release of the stored runs) and this
# repository at one commit with its locked Python environment. The models are
# not in the image: the job copies the exact local blobs from the bucket.
FROM ollama/ollama:0.40.13

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git \
 && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /usr/local/bin/

ENV UV_PYTHON_INSTALL_DIR=/opt/python UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
WORKDIR /opt/sbot
COPY . .
RUN uv sync --frozen --no-dev

ENTRYPOINT ["/bin/bash", "/opt/sbot/infra/gcp/job.sh"]
