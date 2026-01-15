# DMZ IoT Connector - Completion Roadmap

**Date**: January 13, 2026
**Branch**: `feature/standalone-dmz-connector`
**Status**: Foundation Complete (40%), Full Implementation Needed (60%)

## Executive Summary

The DMZ connector has a **solid production-ready foundation**:
- ✅ Docker infrastructure complete
- ✅ Configuration system complete
- ✅ Protobuf schemas complete
- ✅ Core libraries implemented (config loader, backpressure, ZeroBus client)
- ✅ Comprehensive documentation
- ✅ Azure/AWS competitive analysis complete

**Remaining work**: ~3,900 lines of production code across 12 files to complete full production system.

## Current Implementation (40% Complete)

### Infrastructure (100% ✅)
1. **Docker Deployment**
   - Multi-stage Dockerfile with security hardening
   - docker-compose.yml with resource limits
   - docker-entrypoint.sh validation script
   - Non-root execution (UID 1000)

2. **Configuration**
   - config/connector.yaml (400+ options)
   - Support for arbitrary OPC-UA/MQTT/Modbus endpoints
   - Environment variable expansion
   - .env.template

3. **Protobuf Schemas**
   - mqtt_bronze.proto (13 fields)
   - modbus_bronze.proto (14 fields)
   - opcua_bronze.proto (13 fields)
   - INT64 microsecond timestamps

4. **Documentation**
   - README.md (16KB)
   - DEPLOYMENT_GUIDE.md (9KB)
   - STATUS.md (11KB)
   - IMPLEMENTATION_STATUS.md (12KB)
   - AZURE_AWS_FEATURE_ANALYSIS.md (18KB)

### Core Python Modules (30% ✅)

1. **`connector/__init__.py`** ✅ (20 lines)
   - Package initialization
   - Version exports

2. **`connector/config_loader.py`** ✅ (246 lines)
   - YAML + JSON state loading
   - Environment variable expansion (`${VAR_NAME}`)
   - Deep config merging
   - Comprehensive validation
   - Dot-notation access

3. **`connector/backpressure.py`** ✅ (374 lines)
   - Three-tier: memory queue → encrypted disk spool → DLQ
   - AES-256 Fernet encryption
   - Drop policies (OLDEST, NEWEST, REJECT)
   - FIFO guarantees
   - Comprehensive metrics

4. **`connector/zerobus_client.py`** ✅ (330 lines)
   - OAuth2 M2M authentication with Databricks SDK
   - Circuit breaker pattern (CLOSED → OPEN → HALF_OPEN)
   - Exponential backoff with jitter
   - Batch ingestion
   - Retry logic with configurable backoff

## Remaining Implementation (60%)

### Protocol Clients (0% - 3 files, ~1,500 lines)

#### 1. `connector/protocols/__init__.py` (~50 lines)
```python
"""Protocol client abstractions and factory."""
from abc import ABC, abstractmethod

class ProtocolClient(ABC):
    @abstractmethod
    async def connect(self) -> bool: ...
    @abstractmethod
    async def start(self): ...
    @abstractmethod
    async def stop(self): ...
    @abstractmethod
    def get_status(self) -> Dict[str, Any]: ...

def create_protocol_client(source_config, backpressure_mgr) -> ProtocolClient: ...
```

#### 2. `connector/protocols/opcua_client.py` (~600 lines)
**Purpose**: Connect to **arbitrary** customer OPC-UA servers (CLIENT mode, not server)

**Key Differences from Simulator**:
- Uses `asyncua.Client` (not `asyncua.Server`)
- Connects to `config['endpoint']` (e.g., `opc.tcp://192.168.1.100:4840`)
- Subscribes to nodes from `config['nodes']` list
- Supports all security modes: None, Sign, SignAndEncrypt
- Certificate-based authentication
- Automatic reconnection with exponential backoff

**Implementation Pattern**:
```python
class OPCUAClient:
    def __init__(self, source_config, backpressure_mgr):
        self.endpoint = source_config['endpoint']
        self.nodes = source_config['opcua']['nodes']
        self.client = None
        self.subscriptions = []

    async def connect(self):
        """Connect to remote OPC-UA server."""
        self.client = Client(self.endpoint)
        if security_mode != 'None':
            await self.client.set_security(...)
        await self.client.connect()

    async def _subscribe_to_nodes(self):
        """Subscribe to configured node IDs."""
        for node_config in self.nodes:
            node = self.client.get_node(node_config['node_id'])
            handler = DataChangeHandler(self.backpressure_mgr)
            await subscription.subscribe_data_change(node, handler)
```

#### 3. `connector/protocols/mqtt_client.py` (~500 lines)
**Purpose**: Connect to arbitrary MQTT brokers

**Features**:
- aiomqtt library for async MQTT
- TLS 1.2/1.3 support
- Client certificates
- Topic wildcards (`plant/sensors/#`)
- QoS 0/1/2
- JSON/string/binary payload parsing
- Automatic reconnection

**Implementation Pattern**:
```python
class MQTTClient:
    def __init__(self, source_config, backpressure_mgr):
        self.broker = source_config['endpoint']  # mqtt://192.168.1.50:1883
        self.topics = source_config['mqtt']['topics']
        self.client = None

    async def connect(self):
        """Connect to MQTT broker."""
        self.client = Client(hostname, port, tls_context=...)
        await self.client.connect()

    async def _subscribe_loop(self):
        """Subscribe to topics and handle messages."""
        async with self.client.messages() as messages:
            for topic in self.topics:
                await self.client.subscribe(topic)
            async for message in messages:
                await self._handle_message(message)
```

#### 4. `connector/protocols/modbus_client.py` (~400 lines)
**Purpose**: Connect to Modbus TCP/RTU devices

**Features**:
- pymodbus library
- TCP and RTU (serial) support
- Poll register addresses from config
- Data type conversions (int16, uint16, float32, etc.)
- Scaling and offset
- Configurable polling interval

**Implementation Pattern**:
```python
class ModbusClient:
    def __init__(self, source_config, backpressure_mgr):
        self.host = source_config['endpoint']  # 192.168.1.75
        self.registers = source_config['modbus']['registers']
        self.client = None
        self.poll_interval = source_config['modbus']['poll_interval_ms'] / 1000

    async def connect(self):
        """Connect to Modbus device."""
        if protocol == 'TCP':
            self.client = ModbusTcpClient(host, port)
        else:
            self.client = ModbusSerialClient(port='/dev/ttyUSB0')

    async def _poll_loop(self):
        """Poll registers at configured interval."""
        while self.running:
            for reg_config in self.registers:
                result = await self.client.read_holding_registers(addr, count)
                value = self._convert_data_type(result, reg_config['data_type'])
                await self.backpressure_mgr.enqueue(record)
            await asyncio.sleep(self.poll_interval)
```

### Web GUI (0% - 3 files, ~1,500 lines)

#### 5. `connector/web_gui/server.py` (~300 lines)
**Purpose**: aiohttp web server

**Features**:
- Serve HTML/JS on port 8080
- WebSocket for real-time updates
- REST API routing
- Session management
- File upload for certificates

**Implementation Pattern**:
```python
class WebGUIServer:
    def __init__(self, config, backpressure_mgr, zerobus_client, protocol_clients):
        self.app = web.Application()
        self.app.router.add_static('/static', 'web_gui/static')
        self.app.router.add_routes([
            web.get('/', self.index),
            web.get('/api/status', self.get_status),
            web.get('/ws', self.websocket_handler),
            ...
        ])

    async def start(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()
```

#### 6. `connector/web_gui/api.py` (~500 lines)
**Purpose**: REST API handlers

**Endpoints**:
```python
# Configuration
GET  /api/config                # Get current config
POST /api/config                # Update config (saves to connector_state.json)

# Data Sources
GET  /api/sources               # List all data sources
POST /api/sources               # Add new data source
PUT  /api/sources/:id           # Update data source
DELETE /api/sources/:id         # Remove data source
POST /api/sources/:id/test      # Test connection

# Certificates
POST /api/certs/upload          # Upload certificate files

# Status & Metrics
GET  /api/status                # Connector status
GET  /api/metrics               # Backpressure + ZeroBus metrics
GET  /api/sources/:id/status    # Individual source status

# Logs
GET  /api/logs                  # Recent log entries
```

#### 7. `connector/web_gui/templates/index.html` (~800 lines)
**Purpose**: Single-page web UI

**Tabs**:
1. **ZeroBus Configuration**
   - Workspace host
   - OAuth2 client ID/secret
   - Target catalog/schema/table
   - Test connection button

2. **Data Sources** (CRUD)
   - Table of sources (name, protocol, endpoint, status)
   - Add/Edit modal with protocol-specific fields
   - Test connection button per source
   - Enable/disable toggle

3. **Monitoring Dashboard**
   - Real-time charts (Chart.js)
   - Records ingested (counter)
   - Queue depth (gauge)
   - Backpressure metrics
   - Circuit breaker status

4. **Logs Viewer**
   - Tail recent logs
   - Filter by level (INFO, WARNING, ERROR)
   - Auto-refresh

5. **Settings**
   - Backpressure configuration
   - Retry settings
   - Certificate upload

**Design**:
- Databricks branding (Lava gradient, colors)
- Responsive Bootstrap/Tailwind
- WebSocket for live updates

### Monitoring (0% - 2 files, ~300 lines)

#### 8. `connector/monitoring/prometheus.py` (~200 lines)
**Purpose**: Prometheus metrics exporter

**Metrics**:
```python
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Counters
records_read_total = Counter('connector_records_read_total', 'Records read from sources', ['source_name', 'protocol'])
records_written_total = Counter('connector_records_written_total', 'Records written to ZeroBus')
errors_total = Counter('connector_errors_total', 'Errors by type', ['error_type'])

# Gauges
queue_depth = Gauge('connector_queue_depth', 'Current backpressure queue depth')
spool_size_mb = Gauge('connector_spool_size_mb', 'Current spool directory size in MB')
sources_connected = Gauge('connector_sources_connected', 'Number of connected sources')

# Histograms
ingestion_latency_seconds = Histogram('connector_ingestion_latency_seconds', 'Ingestion latency')

class PrometheusExporter:
    def start(self, port=9090):
        start_http_server(port)

    def update_metrics(self, backpressure_mgr, zerobus_client, protocol_clients):
        """Update all gauges with current values."""
```

#### 9. `connector/monitoring/health.py` (~100 lines)
**Purpose**: Health check endpoint

**Response Format**:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-13T10:30:00Z",
  "version": "1.0.0",
  "zerobus": {
    "connected": true,
    "circuit_breaker_state": "closed"
  },
  "sources": [
    {
      "name": "plant_floor_opcua",
      "protocol": "opcua",
      "status": "connected",
      "records_read": 15234
    }
  ],
  "backpressure": {
    "queue_depth": 42,
    "spool_size_mb": 2.3,
    "records_dropped": 0
  }
}
```

###Utilities (0% - 2 files, ~350 lines)

#### 10. `connector/utils/crypto.py` (~200 lines)
**Purpose**: Credential encryption

**Features**:
- Fernet encryption for secrets
- Key management (auto-generation, rotation)
- Encrypt OAuth client secret
- Encrypt protocol passwords
- Store in `certs/secrets_encryption.key`

**Implementation**:
```python
class CredentialManager:
    def __init__(self, key_file='certs/secrets_encryption.key'):
        self.cipher = self._load_or_create_key(key_file)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt and return base64-encoded ciphertext."""

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt base64-encoded ciphertext."""
```

#### 11. `connector/utils/certs.py` (~150 lines)
**Purpose**: Certificate management

**Features**:
- Certificate validation
- Expiry checking
- Auto-rotation warnings
- Key pair generation

**Implementation**:
```python
class CertificateManager:
    def validate_certificate(self, cert_path) -> bool:
        """Validate certificate and check expiry."""

    def days_until_expiry(self, cert_path) -> int:
        """Return days until certificate expires."""

    def should_rotate(self, cert_path, days_before=30) -> bool:
        """Check if certificate should be rotated."""
```

### Main Entry Point (0% - 1 file, ~250 lines)

#### 12. `connector/__main__.py` (~250 lines)
**Purpose**: Main application entry point

**Responsibilities**:
- CLI argument parsing
- Load configuration
- Initialize all components
- Start protocol clients
- Start Web GUI server
- Start monitoring endpoints
- Graceful shutdown handling

**Implementation Pattern**:
```python
import argparse
import asyncio
import signal

async def main():
    # Parse CLI args
    parser = argparse.ArgumentParser(description='Databricks IoT Connector')
    parser.add_argument('--config-dir', default='config')
    parser.add_argument('--web-port', type=int, default=8080)
    parser.add_argument('--metrics-port', type=int, default=9090)
    args = parser.parse_args()

    # Load configuration
    config_loader = ConfigLoader(args.config_dir)
    config = config_loader.load()

    # Initialize core components
    backpressure_mgr = BackpressureManager(config['backpressure'])
    zerobus_client = ZeroBusClient(config)
    await zerobus_client.connect()

    # Initialize protocol clients
    protocol_clients = []
    for source in config['sources']:
        if not source.get('enabled', True):
            continue
        client = create_protocol_client(source, backpressure_mgr)
        await client.connect()
        protocol_clients.append(client)

    # Start data ingestion loop
    ingestion_task = asyncio.create_task(ingestion_loop(backpressure_mgr, zerobus_client))

    # Start Web GUI
    web_server = WebGUIServer(config, backpressure_mgr, zerobus_client, protocol_clients)
    await web_server.start()

    # Start monitoring
    prometheus_exporter = PrometheusExporter()
    prometheus_exporter.start(args.metrics_port)

    # Setup graceful shutdown
    stop_event = asyncio.Event()
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: stop_event.set())

    # Wait for shutdown signal
    await stop_event.wait()

    # Graceful shutdown
    logger.info("Shutting down...")
    await zerobus_client.close()
    for client in protocol_clients:
        await client.stop()
    await backpressure_mgr.clear()

if __name__ == '__main__':
    asyncio.run(main())
```

### Data Ingestion Loop (in `__main__.py`)
```python
async def ingestion_loop(backpressure_mgr, zerobus_client):
    """Continuously dequeue records and send to ZeroBus."""
    batch = []
    batch_timeout = 5.0  # seconds
    last_send_time = time.time()

    while True:
        # Try to dequeue record
        record = await backpressure_mgr.dequeue()

        if record:
            batch.append(record)

        # Send batch if full or timeout reached
        if len(batch) >= 1000 or (batch and time.time() - last_send_time >= batch_timeout):
            success = await zerobus_client.send_batch(batch)
            if success:
                batch.clear()
                last_send_time = time.time()
            else:
                # Re-enqueue failed batch
                for r in batch:
                    await backpressure_mgr.enqueue(r)
                batch.clear()
                await asyncio.sleep(5)  # Backoff before retry

        await asyncio.sleep(0.01)  # Prevent busy loop
```

## Testing Plan

### Unit Tests (~500 lines across test files)

```bash
# Test structure
tests/
  test_config_loader.py
  test_backpressure.py
  test_zerobus_client.py
  test_opcua_client.py
  test_mqtt_client.py
  test_modbus_client.py
  test_web_api.py
```

### Integration Tests
```bash
# Test with real endpoints
python -m connector --config-dir test_configs/opcua_test

# Expected output:
# ✓ Config loaded: 1 sources configured
# ✓ ZeroBus connected: https://e2-demo.cloud.databricks.com
# ✓ OPC-UA client connected: opc.tcp://localhost:4840
# ✓ Web GUI started: http://0.0.0.0:8080
# ✓ Prometheus exporter: http://0.0.0.0:9090
# ✓ Ingestion started: 0 records/sec
```

### Docker Test
```bash
# Build and run
docker-compose up -d

# Check health
curl http://localhost:8080/health

# Check metrics
curl http://localhost:9090/metrics

# View logs
docker-compose logs -f iot-connector
```

## Implementation Estimate

| Component | Lines | Complexity | Time Est. |
|-----------|-------|------------|-----------|
| Protocol Clients (3) | 1,500 | High | 2 days |
| Web GUI (3) | 1,500 | Medium | 2 days |
| Monitoring (2) | 300 | Low | 0.5 days |
| Utilities (2) | 350 | Low | 0.5 days |
| Main Entry Point (1) | 250 | Medium | 0.5 days |
| Testing & Integration | 500 | Medium | 1 day |
| **TOTAL** | **~4,400** | | **~7 days** |

## Recommended Next Steps

### Option A: Complete Full Implementation
Implement all remaining modules for full production system (7 days est.)

### Option B: Core Functionality First
1. Implement protocol clients (2 days)
2. Implement main entry point (0.5 days)
3. Test end-to-end ingestion (0.5 days)
4. **Then** add Web GUI + monitoring (3 days)

### Option C: MVP Demo
1. Implement OPC-UA client only (0.5 days)
2. Implement basic main loop (0.5 days)
3. Test with simulator (0.5 days)
4. Demo working connector → ZeroBus ingestion

## Current Status Summary

**What Works Today**:
- Docker infrastructure ready to deploy
- Configuration system ready for use
- Backpressure management ready for production
- ZeroBus client ready for authentication and batch ingestion

**What's Needed**:
- Protocol clients to actually read data from sources
- Main entry point to orchestrate everything
- Web GUI for non-technical configuration
- Monitoring for production observability

**Recommendation**: Proceed with Option B (core functionality first) to get a working connector ASAP, then add GUI/monitoring for production deployment.
