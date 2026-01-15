#!/bin/bash
# Docker entrypoint script for Databricks IoT Connector
# Handles initialization, validation, and graceful shutdown

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Trap signals for graceful shutdown
cleanup() {
    log "Received shutdown signal, cleaning up..."

    # Send SIGTERM to child processes
    if [ ! -z "$CONNECTOR_PID" ]; then
        kill -TERM "$CONNECTOR_PID" 2>/dev/null || true
        wait "$CONNECTOR_PID"
    fi

    log "Shutdown complete"
    exit 0
}

trap cleanup SIGTERM SIGINT SIGQUIT

# Banner
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║     Databricks IoT Connector for DMZ Deployment          ║
║     Version 1.0.0                                         ║
║                                                           ║
║     Protocols: OPC-UA | MQTT | Modbus TCP/RTU            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF

# Validate required environment variables
log "Validating environment variables..."

REQUIRED_VARS=(
    "DATABRICKS_CLIENT_ID"
    "DATABRICKS_CLIENT_SECRET"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    error "Missing required environment variables: ${MISSING_VARS[*]}"
    error "Please set these variables in your .env file or docker-compose.yml"
    exit 1
fi

log "Environment variables validated ✓"

# Validate config file exists
CONFIG_FILE="${CONFIG_PATH:-/app/config/connector.yaml}"
if [ ! -f "$CONFIG_FILE" ]; then
    error "Configuration file not found: $CONFIG_FILE"
    error "Please mount your config directory: -v ./config:/app/config:ro"
    exit 1
fi

log "Configuration file found: $CONFIG_FILE ✓"

# Check directory permissions
log "Checking directory permissions..."

WRITABLE_DIRS=(
    "/app/spool"
    "/app/logs"
)

for dir in "${WRITABLE_DIRS[@]}"; do
    if [ ! -w "$dir" ]; then
        error "Directory $dir is not writable"
        exit 1
    fi
done

log "Directory permissions OK ✓"

# Validate certificates if TLS is enabled
log "Checking certificates..."

if grep -q "enabled: true" "$CONFIG_FILE" 2>/dev/null; then
    CERT_DIRS=(
        "/app/certs/opcua"
        "/app/certs/mqtt"
    )

    for cert_dir in "${CERT_DIRS[@]}"; do
        if [ -d "$cert_dir" ]; then
            cert_count=$(find "$cert_dir" -type f \( -name "*.crt" -o -name "*.pem" -o -name "*.der" \) | wc -l)
            if [ $cert_count -gt 0 ]; then
                log "Found $cert_count certificate(s) in $cert_dir ✓"
            fi
        fi
    done
fi

# Test network connectivity to Databricks
log "Testing connectivity to Databricks..."

# Extract workspace host from config if not set
if [ -z "$DATABRICKS_WORKSPACE_HOST" ]; then
    DATABRICKS_WORKSPACE_HOST=$(grep "workspace_host:" "$CONFIG_FILE" | head -1 | awk '{print $2}' | tr -d '"')
fi

if [ ! -z "$DATABRICKS_WORKSPACE_HOST" ]; then
    if timeout 10 curl -s -o /dev/null -w "%{http_code}" "$DATABRICKS_WORKSPACE_HOST" | grep -q "200\|401\|403"; then
        log "Databricks workspace is reachable ✓"
    else
        warn "Could not reach Databricks workspace: $DATABRICKS_WORKSPACE_HOST"
        warn "Check your network configuration and firewall rules"
    fi
fi

# Display configuration summary
log "Configuration Summary:"
log "  Config File: $CONFIG_FILE"
log "  Log Level: ${LOG_LEVEL:-INFO}"
log "  Spool Directory: /app/spool"
log "  Logs Directory: /app/logs"
log "  Health Check: http://localhost:8080/health"
log "  Metrics: http://localhost:9090/metrics"

# Export environment variables for Python
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Start the connector
log "Starting Databricks IoT Connector..."
log "Process ID: $$"

# Run the connector in the background so we can trap signals
"$@" &
CONNECTOR_PID=$!

log "Connector started with PID: $CONNECTOR_PID"

# Wait for the process
wait $CONNECTOR_PID
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    error "Connector exited with code: $EXIT_CODE"
else
    log "Connector exited normally"
fi

exit $EXIT_CODE
