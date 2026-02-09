FROM python:3.11-slim
LABEL org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src/ ./src/
COPY tests/ ./tests/
RUN pip install --upgrade pip setuptools wheel
RUN pip install ".[dev]"

ENV PYTHONPATH=/app/src
ENV MCP_TRANSPORT=sse
ENV PORT=8084
ENV PYTHONUNBUFFERED=1

# Run the server
CMD ["python", "-m", "talos_ucp_connector.adapters.inbound.mcp_server"]
