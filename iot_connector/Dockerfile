# Multi-stage Dockerfile for Databricks IoT Connector
# Production-ready container for DMZ deployment

# Stage 1: Builder
FROM python:3.11-slim AS builder

LABEL maintainer="Databricks Solutions Architecture"
LABEL description="Databricks IoT Connector for OPC-UA, MQTT, and Modbus protocols"
LABEL version="1.0.0"

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libssl-dev \
    libffi-dev \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r connector && \
    useradd -r -g connector -u 1000 -m -s /bin/bash connector

# Set working directory
WORKDIR /app

# Copy wheels from builder
COPY --from=builder /build/wheels /tmp/wheels

# Install Python packages from wheels
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir /tmp/wheels/* && \
    rm -rf /tmp/wheels

# Copy application code
COPY --chown=connector:connector connector/ ./connector/
COPY --chown=connector:connector protos/ ./protos/

# Copy protobuf schemas
COPY --chown=connector:connector protos/*.proto ./protos/

# Compile protobuf schemas
RUN python -m grpc_tools.protoc \
    --proto_path=./protos \
    --python_out=./protos \
    ./protos/*.proto

# Create necessary directories with correct permissions
RUN mkdir -p \
    /app/config \
    /app/certs/opcua \
    /app/certs/mqtt \
    /app/certs/modbus \
    /app/spool \
    /app/spool/dlq \
    /app/logs \
    && chown -R connector:connector /app

# Switch to non-root user
USER connector

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_LEVEL=INFO \
    CONFIG_PATH=/app/config/connector.yaml

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose ports
EXPOSE 8080 9090

# Volume mounts for persistent data
VOLUME ["/app/config", "/app/certs", "/app/spool", "/app/logs"]

# Entrypoint script
COPY --chown=connector:connector docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "-m", "connector"]
