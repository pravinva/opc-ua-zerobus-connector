# Databricks IoT Connector for DMZ Deployment

Production-ready, standalone connector for streaming industrial IoT data from OPC-UA, MQTT, and Modbus sources to Databricks Unity Catalog via ZeroBus SDK.

## Features

- **Multi-Protocol Support**: OPC-UA, MQTT, Modbus TCP/RTU
- **Production-Ready**: Backpressure management, disk spooling, circuit breakers
- **Security**: TLS/SSL, certificate management, encrypted credentials
- **Monitoring**: Prometheus metrics, OpenTelemetry tracing, structured logging
- **Resilience**: Automatic reconnection, retry logic, health checks
- **Containerized**: Docker/Colima deployment for DMZ environments

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DMZ Environment                           │
│                                                              │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐        │
│  │  OPC-UA    │    │    MQTT    │    │   Modbus   │        │
│  │  Servers   │    │   Brokers  │    │  Devices   │        │
│  └──────┬─────┘    └──────┬─────┘    └──────┬─────┘        │
│         │                 │                  │               │
│         └─────────────────┴──────────────────┘               │
│                           │                                  │
│         ┌─────────────────▼────────────────────┐             │
│         │  Databricks IoT Connector Container  │             │
│         │  ┌──────────────────────────────┐    │             │
│         │  │   Protocol Clients           │    │             │
│         │  │  - OPC-UA (Sign & Encrypt)   │    │             │
│         │  │  - MQTT (TLS 1.2/1.3)        │    │             │
│         │  │  - Modbus TCP/RTU            │    │             │
│         │  └─────────────┬────────────────┘    │             │
│         │                │                     │             │
│         │  ┌─────────────▼────────────────┐    │             │
│         │  │  Backpressure Management     │    │             │
│         │  │  - Memory Queue (10K records)│    │             │
│         │  │  - Disk Spool (1GB encrypted)│    │             │
│         │  │  - Dead Letter Queue         │    │             │
│         │  └─────────────┬────────────────┘    │             │
│         │                │                     │             │
│         │  ┌─────────────▼────────────────┐    │             │
│         │  │  ZeroBus SDK (Protobuf)      │    │             │
│         │  │  - Batch ingestion           │    │             │
│         │  │  - Circuit breaker           │    │             │
│         │  │  - Retry with backoff        │    │             │
│         │  └─────────────┬────────────────┘    │             │
│         └────────────────┼──────────────────────┘             │
│                          │ HTTPS/443                         │
└──────────────────────────┼───────────────────────────────────┘
                           │
                           │ Firewall (egress only)
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                  Databricks Workspace                         │
│  ┌────────────────────────────────────────────────┐           │
│  │  ZeroBus Ingestion Endpoint                    │           │
│  │  - OAuth2 Service Principal Auth               │           │
│  │  - Schema validation                           │           │
│  │  - Rate limiting                               │           │
│  └───────────────────┬────────────────────────────┘           │
│                      │                                        │
│  ┌───────────────────▼────────────────────────────┐           │
│  │  Unity Catalog Delta Tables                    │           │
│  │  - mqtt.scada_data.mqtt_events_bronze          │           │
│  │  - modbus.scada_data.modbus_events_bronze      │           │
│  │  - opcua.scada_data.opcua_events_bronze        │           │
│  └────────────────────────────────────────────────┘           │
└───────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker or Colima
- Databricks workspace with ZeroBus enabled
- Service Principal with appropriate permissions
- Network access to industrial devices and Databricks

### Installation

1. **Clone repository**:
```bash
git clone https://github.com/your-org/databricks-iot-connector.git
cd databricks-iot-connector/databricks_iot_connector
```

2. **Configure environment**:
```bash
cp .env.template .env
# Edit .env with your credentials
vi .env
```

3. **Configure connector**:
```bash
# Edit config/connector.yaml with your device endpoints
vi config/connector.yaml
```

4. **Add certificates** (if using TLS):
```bash
# OPC-UA certificates
cp your-opcua-cert.der certs/opcua/client_cert.der
cp your-opcua-key.pem certs/opcua/client_key.pem

# MQTT certificates
cp your-mqtt-ca.crt certs/mqtt/ca.crt
cp your-mqtt-client.crt certs/mqtt/client.crt
cp your-mqtt-client.key certs/mqtt/client.key
```

5. **Build and run**:
```bash
# Using Docker
docker-compose up -d

# Using Colima
colima start
docker-compose up -d
```

6. **Check health**:
```bash
curl http://localhost:8080/health
curl http://localhost:9090/metrics
```

## Configuration

### ZeroBus Connection

Edit `config/connector.yaml`:

```yaml
zerobus:
  workspace_host: "https://your-workspace.cloud.databricks.com"
  zerobus_endpoint: "your-endpoint.zerobus.region.cloud.databricks.com"

  auth:
    client_id: "${DATABRICKS_CLIENT_ID}"
    client_secret: "${DATABRICKS_CLIENT_SECRET}"

  target:
    catalog: "iot_data"
    schema: "bronze"
    table: "sensor_events"
```

### OPC-UA Source

```yaml
sources:
  - name: "plant_floor_opcua"
    protocol: "opcua"
    enabled: true
    endpoint: "opc.tcp://192.168.1.100:4840"

    opcua:
      security_policy: "Basic256Sha256"
      security_mode: "SignAndEncrypt"
      certificate_path: "certs/opcua/client_cert.der"
      private_key_path: "certs/opcua/client_key.pem"
      username: "${OPCUA_USERNAME}"
      password: "${OPCUA_PASSWORD}"

      nodes:
        - node_id: "ns=2;s=Temperature"
          sampling_interval_ms: 1000
        - browse_path: "0:Root/0:Objects/2:ProcessArea"
          recursive: true
```

### MQTT Source

```yaml
sources:
  - name: "sensor_network_mqtt"
    protocol: "mqtt"
    enabled: true
    endpoint: "mqtt://192.168.1.200:1883"

    mqtt:
      tls:
        enabled: true
        ca_cert_path: "certs/mqtt/ca.crt"
        client_cert_path: "certs/mqtt/client.crt"
        client_key_path: "certs/mqtt/client.key"

      username: "${MQTT_USERNAME}"
      password: "${MQTT_PASSWORD}"

      topics:
        - topic: "sensors/+/temperature"
          qos: 1
```

### Modbus Source

```yaml
sources:
  - name: "plc_modbus_tcp"
    protocol: "modbus"
    enabled: true
    endpoint: "modbus+tcp://192.168.1.150:502"

    modbus:
      slave_id: 1
      poll_interval_seconds: 1

      registers:
        - address: 40001
          count: 10
          register_type: "holding"
          data_type: "float32"
```

## Production Features

### Backpressure Management

The connector handles data surges gracefully:

1. **Memory Queue**: 10,000 records in-memory buffer
2. **Disk Spooling**: 1GB encrypted disk buffer when memory is full
3. **Drop Policies**: Configurable (oldest/newest/reject)
4. **Dead Letter Queue**: Isolate invalid records

```yaml
backpressure:
  enabled: true
  memory_queue:
    max_size: 10000
    drop_policy: "oldest"
  disk_spool:
    enabled: true
    max_size_mb: 1000
    encryption: true
```

### Resilience

- **Circuit Breaker**: Open circuit after 5 failures, retry after 60s
- **Exponential Backoff**: 1s → 2s → 4s → ... → 300s max
- **Automatic Reconnection**: Infinite retries with backoff
- **Health Checks**: HTTP endpoint every 30s

```yaml
resilience:
  circuit_breaker:
    enabled: true
    failure_threshold: 5
    timeout_seconds: 60

  reconnect:
    initial_delay_seconds: 1
    max_delay_seconds: 300
    backoff_multiplier: 2
```

### Security

- **TLS/SSL**: All protocols support encryption
- **Certificate Management**: Auto-rotation before expiry
- **Encrypted Spooling**: AES-256 for disk data
- **OAuth2**: Service Principal authentication
- **Non-root Container**: Runs as user `connector` (UID 1000)

```yaml
security:
  certificates:
    auto_rotation: true
    rotation_days_before_expiry: 30

  network:
    required_outbound:
      - "*.cloud.databricks.com:443"
      - "*.zerobus.*.cloud.databricks.com:443"
```

### Monitoring

**Prometheus Metrics** (`http://localhost:9090/metrics`):
- `records_read_total` - Total records read from sources
- `records_written_total` - Total records written to ZeroBus
- `records_failed_total` - Total failed records
- `batch_latency_seconds` - Batch processing latency
- `queue_depth` - Current queue size
- `connection_status` - Source connection status

**OpenTelemetry Tracing**:
```yaml
monitoring:
  tracing:
    enabled: true
    otlp:
      endpoint: "http://localhost:4318"
```

**Structured Logging**:
```yaml
monitoring:
  logging:
    level: "INFO"
    format: "json"
    file_path: "logs/connector.log"
```

## Deployment

### Docker Compose

```bash
# Start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Restart
docker-compose restart
```

### Colima (macOS/Linux)

```bash
# Install Colima
brew install colima

# Start Colima
colima start --cpu 2 --memory 4

# Deploy
docker-compose up -d

# Monitor
docker-compose ps
docker-compose logs -f iot-connector
```

### Kubernetes (Advanced)

```bash
# Convert docker-compose to k8s manifests
kompose convert -f docker-compose.yml

# Deploy to k8s
kubectl apply -f iot-connector-deployment.yaml
kubectl apply -f iot-connector-service.yaml

# Check status
kubectl get pods
kubectl logs -f pod/iot-connector-xxx
```

## Networking

### Firewall Rules

**Inbound** (from industrial devices to connector):
- OPC-UA: TCP/4840 (or custom port)
- MQTT: TCP/1883 (non-TLS) or TCP/8883 (TLS)
- Modbus TCP: TCP/502
- Health Check: TCP/8080
- Metrics: TCP/9090

**Outbound** (from connector to Databricks):
- Databricks Workspace: TCP/443 to `*.cloud.databricks.com`
- ZeroBus Endpoint: TCP/443 to `*.zerobus.*.cloud.databricks.com`

### Host Network Mode

For direct device access, use host networking:

```yaml
# docker-compose.yml
services:
  iot-connector:
    network_mode: "host"
```

Note: This bypasses Docker networking and exposes all ports.

## Troubleshooting

### Check Logs

```bash
# Container logs
docker-compose logs -f iot-connector

# File logs
tail -f logs/connector.log | jq .

# Check spool directory
ls -lh spool/
```

### Health Check

```bash
# HTTP health endpoint
curl http://localhost:8080/health

# Expected response
{
  "status": "healthy",
  "sources": {
    "plant_floor_opcua": "connected",
    "sensor_network_mqtt": "connected",
    "plc_modbus_tcp": "connected"
  },
  "zerobus": "connected",
  "queue_depth": 42,
  "uptime_seconds": 3600
}
```

### Common Issues

**"Connection refused" to OPC-UA/MQTT/Modbus**:
- Check endpoint URLs in `config/connector.yaml`
- Verify network connectivity: `docker exec iot-connector ping 192.168.1.100`
- Check firewall rules
- Use host network mode if needed

**"OAuth authentication failed"**:
- Verify service principal client ID/secret
- Check token endpoint URL
- Ensure service principal has permissions on target catalog/schema

**"Circuit breaker open"**:
- Check ZeroBus endpoint reachability
- Review error logs for root cause
- Wait for circuit breaker timeout (default 60s)
- Check Databricks workspace status

**"Queue full, dropping records"**:
- Increase memory queue size
- Enable disk spooling
- Check ZeroBus ingestion rate
- Review network bandwidth

## Performance Tuning

### Threading

```yaml
performance:
  workers:
    reader_threads: 4  # Concurrent source readers
    writer_threads: 2  # Concurrent ZeroBus writers
```

### Batching

```yaml
processing:
  batch:
    max_size: 100  # Records per batch
    max_wait_seconds: 5  # Max time before sending partial batch
```

### Memory

```yaml
performance:
  memory:
    max_heap_mb: 2048
    gc_strategy: "G1GC"
```

## Data Schemas

### MQTT Schema

```protobuf
message MQTTBronzeRecord {
  int64 event_time = 1;  // Microseconds since epoch
  int64 ingest_time = 2;
  string source_name = 3;
  string topic = 4;
  string industry = 5;
  string sensor_name = 6;
  double value = 7;
  string unit = 9;
  int32 qos = 12;
}
```

### Modbus Schema

```protobuf
message ModbusBronzeRecord {
  int64 event_time = 1;
  int64 ingest_time = 2;
  string source_name = 3;
  int32 slave_id = 4;
  int32 register_address = 5;
  string register_type = 6;
  double raw_value = 12;
  int32 scaled_value = 13;
}
```

### OPC-UA Schema

```protobuf
message OPCUABronzeRecord {
  int64 event_time = 1;
  int64 ingest_time = 2;
  string source_name = 3;
  string endpoint = 4;
  int32 namespace = 5;
  string node_id = 6;
  int64 status_code = 8;
  double value_num = 12;
}
```

## Security Best Practices

1. **Rotate Service Principal Secrets** every 90 days
2. **Use TLS for all protocols** (OPC-UA SignAndEncrypt, MQTT TLS 1.2+)
3. **Encrypt disk spool** with strong keys
4. **Run as non-root** (default: UID 1000)
5. **Read-only root filesystem** (except /app/spool, /app/logs)
6. **No privileged mode** (security_opt: no-new-privileges)
7. **Limit container resources** (CPU: 2, Memory: 2GB)

## License

Copyright © 2024 Databricks, Inc. All rights reserved.

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/databricks-iot-connector/issues
- Databricks Support: https://help.databricks.com

## Changelog

### v1.0.0 (2024-01-13)
- Initial release
- Multi-protocol support (OPC-UA, MQTT, Modbus)
- Production-ready backpressure management
- Docker/Colima deployment
- Prometheus metrics and OpenTelemetry tracing
