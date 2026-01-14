# Databricks IoT Connector & OT Data Simulator

A **professional-grade edge connector** and **industrial OT data simulator** supporting **OPC-UA, MQTT, and Modbus** protocols, with advanced visualization, natural language control, and W3C WoT integration.

## 🌟 Key Features

### Connector Features
- **Multi-Protocol Support**: OPC-UA, MQTT (TLS), Modbus TCP/RTU
- **Zerobus Integration**: Stream to Databricks Unity Catalog via gRPC
- **Automatic Reconnection**: Exponential backoff after network outages
- **Backpressure Handling**: Configurable queue limits and drop policies
- **Rate Limiting**: Prevent overwhelming downstream systems
- **Prometheus Metrics**: Comprehensive monitoring
- **Zero Dependencies**: Runs anywhere Docker runs

### Simulator Features (NEW!)
- **379 Industrial Sensors** across 16 industries (mining, utilities, oil & gas, manufacturing, aerospace, water, space, etc.)
- **Advanced Visualizations**: 5 training-grade visualizations (FFT, Spectrogram, SPC Charts, Correlation Analysis)
- **Natural Language Control**: AI-powered operator using Claude Sonnet 4.5
- **W3C WoT Thing Descriptions**: 379 semantic-enabled sensors with SAREF/SOSA/QUDT ontologies
- **OPC UA Security**: OPC UA 10101 compliant (Basic256Sha256, certificate auth)
- **Real-Time Web UI**: Professional Databricks-branded interface with Chart.js 4.4.0
- **WebSocket Streaming**: Sub-second latency (500ms updates)
- **Fault Injection**: Simulate equipment failures for testing

---

## 🚀 Quick Start

### Simulator Only (Local Development)

```bash
# Clone repository
git clone https://github.com/pravinva/opc-ua-zerobus-connector.git
cd opc-ua-zerobus-connector

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run simulator with web UI
python -m ot_simulator --web-ui --config ot_simulator/config.yaml
```

**Access**:
- **Web UI**: http://localhost:8989 (enhanced visualizations)
- **OPC UA Endpoint**: opc.tcp://localhost:4840/ot-simulator/server/
- **MQTT Broker**: mqtt://localhost:1883 (if enabled)
- **Modbus TCP**: modbus://localhost:502 (if enabled)

### Connector + Simulator (Full Stack)

```bash
# Start connector with simulator integration
python -m opcua2uc --config ./connector_config_databricks_apps.yaml
```

### Docker Deployment

```bash
# Build image
docker build -t iot-connector:latest .

# Run connector
docker run --rm -p 8080:8080 -p 9090:9090 \
  -e DBX_CLIENT_ID="<your-sp-id>" \
  -e DBX_CLIENT_SECRET="<your-sp-secret>" \
  iot-connector:latest
```

---

## 📊 Advanced Visualizations (Training-Grade)

The simulator now includes **5 of 8 priority visualizations** for industrial ML training and diagnostics:

### 1. ✅ FFT Frequency Analysis (Priority 1)
- **Use Case**: Bearing fault detection, vibration analysis
- **Technology**: FFT.js 4.0.3, Cooley-Tukey algorithm
- **Features**:
  - 256-point FFT with Hanning window
  - Bearing defect frequency annotations (BPFO, BPFI, BSF, FTF)
  - Toggle between time-domain and frequency-domain views
  - Logarithmic Y-axis for amplitude (g RMS)
- **Button**: Cyan, appears on vibration sensors

### 2. ✅ Multi-Sensor Overlay + Correlation (Priority 2)
- **Use Case**: Feature engineering for ML, correlation analysis
- **Features**:
  - Overlay up to 8 sensors on single chart
  - Real-time Pearson correlation coefficients
  - Automatic Y-axis assignment by unit type
  - Dual/triple Y-axis support
- **Button**: Blue multi-select with Ctrl+Click

### 3. ✅ Spectrogram (Time-Frequency Heatmap) (Priority 3) - **NEW!**
- **Use Case**: Bearing degradation tracking, transient analysis
- **Features**:
  - STFT (Short-Time Fourier Transform) visualization
  - Bubble chart with time vs frequency
  - Tracks 60 FFT computations (30 seconds history)
  - Magnitude shown by bubble size and opacity
- **Button**: Purple, appears on vibration sensors

### 4. ✅ SPC Charts (Statistical Process Control) (Priority 6) - **NEW!**
- **Use Case**: Manufacturing quality control, Six Sigma compliance
- **Features**:
  - Real-time ±3σ control limits (UCL/LCL)
  - ±2σ warning limits (UWL/LWL)
  - Color-coded points: Blue (in control), Yellow (warning), Red (out of control)
  - 100-sample rolling buffer
- **Button**: Green, appears on ALL sensors

### 5. ✅ Correlation Heatmap Matrix (Priority 4) - **NEW!**
- **Use Case**: Sensor redundancy analysis, ML feature selection
- **Features**:
  - Pairwise Pearson correlations for all active sensors
  - Color gradient: Red (+1) → Gray (0) → Blue (-1)
  - Interactive tooltips with exact values
  - Dynamic sizing based on sensor count
- **Button**: "Correlation Heatmap" in overlay section

**Remaining Visualizations** (roadmap):
- Priority 5: Equipment Health Dashboard (partial)
- Priority 7: 3D Equipment View (5-7 days)
- Priority 8: Waterfall Plot (3-4 days)

**Documentation**: See `docs/VISUALIZATION_STATUS.md` for complete details

---

## 🤖 Natural Language Control

Control the simulator using plain English powered by **Claude Sonnet 4.5**:

```bash
# Start Natural Language interface
python -m ot_simulator.llm_agent_operator

🎤 You: "start the OPC-UA server"
🤖 Agent: ✓ OPCUA started
💭 Starting OPC-UA protocol server on port 4840 with 379 sensors...

🎤 You: "show me all vibration sensors in mining"
🤖 Agent: Found 3 vibration sensors in mining:
  • mining/crusher_1_vibration_x (g)
  • mining/crusher_1_vibration_y (g)
  • mining/vent_fan_1_vibration (g)

🎤 You: "inject a fault into the crusher motor for 30 seconds"
🤖 Agent: ✓ Fault injected into mining/crusher_1_motor_power
💭 Simulating motor overload condition for testing...
```

**Features**:
- Conversational memory (remembers context)
- 6 command categories: start/stop protocols, fault injection, status queries, sensor discovery, chat
- Databricks Foundation Model integration
- Configurable via `llm_agent_config.yaml`

**Documentation**:
- `docs/QUICK_START_NATURAL_LANGUAGE.md` - 5-minute guide
- `docs/NATURAL_LANGUAGE_OPERATOR_GUIDE.md` - Comprehensive 400+ line guide

---

## 🌐 W3C WoT Thing Descriptions

All 379 sensors are exposed as **W3C WoT Thing Descriptions** with semantic metadata:

```json
{
  "@context": ["https://www.w3.org/2022/wot/td/v1.1", "https://w3id.org/saref"],
  "id": "urn:databricks:iot:mining:crusher_1_temperature",
  "title": "Crusher 1 Temperature",
  "@type": ["saref:TemperatureSensor", "sosa:Sensor"],
  "properties": {
    "temperature": {
      "type": "number",
      "unit": "degree Celsius",
      "qudt:unit": "http://qudt.org/vocab/unit/DEG_C",
      "minimum": 20.0,
      "maximum": 150.0,
      "observable": true
    }
  }
}
```

**Features**:
- SAREF (Smart Appliances REFerence) ontology
- SOSA (Sensor, Observation, Sample, and Actuator) ontology
- QUDT (Quantities, Units, Dimensions, Types) units
- Filter by industry, semantic type, or keyword
- 379 sensors × ~150 lines each = ~57,000 lines of semantic metadata

**Web UI**: Browse at http://localhost:8989 → "WoT Browser" tab

---

## 🏭 Supported Industries & Sensors

**16 Industries, 379 Sensors**:

| Industry | Sensors | Examples |
|----------|---------|----------|
| **Mining** | 43 | Crusher vibration, conveyor speed, ventilation fan |
| **Utilities** | 37 | Gas turbine temperature, grid frequency, transformer load |
| **Oil & Gas** | 28 | Pipeline pressure, separator level, pump flow |
| **Manufacturing** | 24 | CNC spindle speed, press force, conveyor position |
| **Renewable Energy** | 22 | Solar panel voltage, wind turbine RPM, battery SOC |
| **Water Treatment** | 20 | Chlorine level, pH, flow rate, pump pressure |
| **Food & Beverage** | 18 | Pasteurizer temperature, fill level, conveyor speed |
| **Pharma** | 16 | Cleanroom pressure, autoclave temp, tablet hardness |
| **Steel** | 14 | Furnace temperature, rolling mill speed, cooling water |
| **Cement** | 14 | Kiln temperature, mill vibration, dust collector |
| **Pulp & Paper** | 12 | Digester pressure, paper moisture, dryer temp |
| **Aerospace** | 10 | Test stand thrust, fuel flow, chamber pressure |
| **Automotive** | 10 | Paint booth temp, welding current, press tonnage |
| **Chemical** | 8 | Reactor pressure, distillation temp, agitator speed |
| **Semiconductor** | 6 | PECVD plasma power, CMP pad pressure, etch rate |
| **Space** | 4 | Payload temperature, solar array voltage, gyro rate |

**Sensor Types**: Temperature, pressure, vibration, flow, level, speed, power, voltage, current, position, and more.

**Realistic Models**: Each sensor uses physics-based equations (heat transfer, fluid dynamics, rotational dynamics) with realistic noise and drift.

---

## 🔐 OPC UA Security (OPC UA 10101 Compliant)

Security is **implemented but disabled by default** for ease of development. Enable in production:

```yaml
# ot_simulator/config.yaml
opcua:
  security:
    enabled: true
    security_policy: "Basic256Sha256"  # OPC UA 10101 recommended
    security_mode: "SignAndEncrypt"
    server_cert_path: "ot_simulator/certs/server_cert.pem"
    server_key_path: "ot_simulator/certs/server_key.pem"
    trusted_certs_dir: "ot_simulator/certs/trusted"
    enable_user_auth: true
    users:
      admin: "change-this-password"
      operator: "operator-password"
```

**Generate Certificates**:
```bash
cd ot_simulator/certs
openssl req -x509 -newkey rsa:2048 -keyout server_key.pem \
  -out server_cert.pem -days 365 -nodes \
  -subj "/CN=ot-simulator/O=Databricks/C=US"
```

**Documentation**: See `docs/SECURITY_IMPLEMENTATION_GUIDE.md`

---

## 🔌 Connecting Ignition SCADA

The OPC UA endpoint can be accessed by **Ignition** or any OPC UA client:

### Local Network
```
Endpoint: opc.tcp://localhost:4840/ot-simulator/server/
Security: None (for testing) or Basic256Sha256 (production)
```

### Cloud Deployment (AWS/Azure)
```
Endpoint: opc.tcp://<public-ip>:4840/ot-simulator/server/
Security: Basic256Sha256 with certificates
```

### Ngrok Tunnel (Quick Demo)
```bash
ngrok tcp 4840
# Use: opc.tcp://0.tcp.ngrok.io:<port>/ot-simulator/server/
```

**Documentation**: See `docs/IGNITION_INTEGRATION_GUIDE.md` for complete setup guide

---

## 🏗️ Architecture

### Overall System

```
┌─────────────────────────────────────────────────────────────┐
│                     OT DATA SIMULATOR                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ OPC UA 4840  │  │ MQTT 1883    │  │ Modbus 502   │      │
│  │ 379 sensors  │  │ Pub/Sub      │  │ TCP/RTU      │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│         └─────────────────┴─────────────────┘               │
│                           │                                 │
│                  ┌────────▼─────────┐                       │
│                  │ SimulatorManager │                       │
│                  │ (Unified Access) │                       │
│                  └────────┬─────────┘                       │
│                           │                                 │
│         ┌─────────────────┼─────────────────┐               │
│         │                 │                 │               │
│   ┌─────▼─────┐  ┌────────▼────────┐  ┌────▼─────┐        │
│   │ Web UI    │  │ WebSocket       │  │   NLP    │        │
│   │ 8989/8000 │  │ Real-time       │  │ Operator │        │
│   │ Chart.js  │  │ 500ms updates   │  │ Claude   │        │
│   └───────────┘  └─────────────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────┘
                           │
                  ┌────────▼─────────┐
                  │   IoT Connector  │
                  │  (This Project)  │
                  └────────┬─────────┘
                           │
                  ┌────────▼─────────┐
                  │     Zerobus      │
                  │  (gRPC Streams)  │
                  └────────┬─────────┘
                           │
                  ┌────────▼─────────┐
                  │   Databricks     │
                  │  Unity Catalog   │
                  │   Delta Tables   │
                  └──────────────────┘
```

### 3-Layer Simulator Architecture

**Layer 1: Data Generation** (Always Running)
- 379 SensorSimulator instances
- Physics-based models with realistic noise
- Independent of protocols

**Layer 2: Data Access** (Always Available)
- SimulatorManager provides unified access
- Fault injection at source level
- Single source of truth for all consumers

**Layer 3: Data Exposure** (Start/Stop Controlled)
- OPC UA, MQTT, Modbus network endpoints
- WebSocket server for web UI
- Protocols read from Layer 2

**Key Insight**: Charts work WITHOUT starting protocols - they bypass Layer 3 and read directly from Layer 2.

---

## 📁 Directory Structure

```
opc-ua-zerobus-connector/
├── opcua2uc/                      # IoT Connector (Edge)
│   ├── core/                      # Core connector logic
│   ├── protocols/                 # Protocol implementations
│   │   ├── opcua/                 # OPC UA client
│   │   ├── mqtt/                  # MQTT subscriber
│   │   └── modbus/                # Modbus master
│   ├── web/                       # REST API & Web UI
│   ├── wot/                       # W3C WoT integration
│   ├── databricks_auth.py         # OAuth client credentials
│   ├── databricks_uc.py           # Unity Catalog writer
│   ├── zerobus_producer.py        # gRPC producer
│   └── metrics.py                 # Prometheus metrics
│
├── ot_simulator/                  # OT Data Simulator
│   ├── sensor_models.py           # 379 sensor definitions
│   ├── simulator_manager.py       # Unified sensor access
│   ├── opcua_simulator.py         # OPC UA server (asyncua)
│   ├── mqtt_simulator.py          # MQTT publisher
│   ├── modbus_simulator.py        # Modbus TCP/RTU server
│   ├── opcua_security.py          # OPC UA 10101 security
│   ├── web_ui/
│   │   └── templates.py           # Advanced visualizations (4200+ lines)
│   ├── websocket_server.py        # Real-time streaming
│   ├── llm_agent_operator.py      # Natural language control
│   ├── config.yaml                # Simulator configuration
│   └── certs/                     # Security certificates
│
├── docs/                          # Documentation
│   ├── VISUALIZATION_STATUS.md   # Visualization roadmap
│   ├── SECURITY_IMPLEMENTATION_GUIDE.md
│   ├── IGNITION_INTEGRATION_GUIDE.md
│   ├── DEPLOYMENT_GUIDE_DATABRICKS_APPS.md
│   └── ... (30+ technical guides)
│
├── tests/                         # Test files
│   ├── test_nl_ai_wot_integration.py
│   └── test_ws_manual.py
│
├── Dockerfile                     # Container build
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

---

## 🎯 Supported Protocols

### OPC-UA (OPC Unified Architecture)
- **Standard**: IEC 62541
- **Security**: OPC UA 10101 (Basic256Sha256)
- **Features**: Subscription-based, automatic discovery, 379 sensors
- **Endpoint**: `opc.tcp://0.0.0.0:4840/ot-simulator/server/`
- **Clients**: UaExpert, Ignition, Kepware, any OPC UA client

### MQTT (Message Queuing Telemetry Transport)
- **Broker Support**: Mosquitto, HiveMQ, AWS IoT Core
- **Security**: TLS/SSL (mqtts://)
- **Features**: Pub/sub, QoS 0/1/2, wildcard topics
- **Topics**: `iot/{industry}/{sensor}` (e.g., `iot/mining/crusher_1_temperature`)
- **Payload**: JSON format

### Modbus (TCP & RTU)
- **Modes**: TCP (Ethernet), RTU (Serial RS-485)
- **Features**: Holding/input registers, coils, discrete inputs
- **Endpoint**: `modbus://0.0.0.0:502` (TCP) or `/dev/ttyUSB0` (RTU)
- **Clients**: ModScan, QModMaster, Ignition Modbus

**Configuration Guide**: See `docs/PROTOCOLS.md`

---

## 📊 Databricks Integration

### Unity Catalog Schema

All protocols stream to a unified table:

```sql
CREATE TABLE IF NOT EXISTS manufacturing.iot_data.events_bronze (
  event_time TIMESTAMP,              -- Event timestamp (microseconds)
  ingest_time TIMESTAMP,             -- Ingestion timestamp
  source_name STRING,                -- Source identifier
  endpoint STRING,                   -- Connection endpoint
  protocol_type STRING,              -- opcua, mqtt, or modbus
  topic_or_path STRING,              -- Protocol-specific path
  value STRING,                      -- Value as string
  value_type STRING,                 -- Data type
  value_num DOUBLE,                  -- Numeric value (if applicable)
  metadata MAP<STRING, STRING>,      -- Protocol-specific metadata
  status_code INT,                   -- Quality/status code
  status STRING                      -- Status description
) USING DELTA;
```

### Zerobus Configuration

```yaml
zerobus:
  endpoint: "https://your-workspace.cloud.databricks.com"
  catalog: "manufacturing"
  schema: "iot_data"
  table: "events_bronze"
  auth:
    client_id: "${DBX_CLIENT_ID}"
    client_secret: "${DBX_CLIENT_SECRET}"
```

### Authentication

Set environment variables:
```bash
export DBX_CLIENT_ID="<service-principal-id>"
export DBX_CLIENT_SECRET="<service-principal-secret>"
```

Test auth: `POST /api/databricks/test_auth`

---

## 🔧 REST API

The connector exposes a REST API on port 8080:

### Status & Monitoring
- `GET /api/status` - Connector status and metrics
- `GET /api/sources` - List configured sources
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe

### Source Management
- `POST /api/sources` - Add new source (auto-detects protocol)
- `DELETE /api/sources/{name}` - Remove source
- `POST /api/sources/{name}/test` - Test connection
- `POST /api/sources/{name}/start` - Start streaming
- `POST /api/sources/{name}/stop` - Stop streaming

### Configuration
- `GET /api/config` - Get full configuration
- `POST /api/config` - Update configuration
- `POST /api/config/patch` - Partial config update
- `POST /api/protocol/detect` - Detect protocol from endpoint

---

## 📈 Monitoring & Metrics

### Prometheus Metrics

Available at `http://localhost:9090/metrics`:

```
# Connector Metrics
connector_connected_sources                    # Active connections
connector_events_ingested_total                # Events from sources
connector_events_sent_total                    # Events to Databricks
connector_events_dropped_total{source="..."}   # Dropped (backpressure)
connector_queue_depth{source="..."}            # Queue size

# Simulator Metrics
simulator_active_sensors                       # Running sensors
simulator_fault_injections_total               # Fault events
simulator_websocket_connections                # Active clients
```

### Web UI Metrics

Real-time dashboard showing:
- Connected protocols (OPC UA, MQTT, Modbus)
- Active sensor count
- Update rates and latency
- Chart count and correlation heatmaps

---

## 🚢 Deployment Options

### 1. Local Development
```bash
python -m ot_simulator --web-ui --config ot_simulator/config.yaml
```

### 2. Docker Container
```bash
docker build -t iot-connector:latest .
docker run -d --name iot-connector \
  -p 8080:8080 -p 9090:9090 -p 4840:4840 \
  iot-connector:latest
```

### 3. Databricks Apps
```bash
databricks apps deploy ot-simulator --config app.yaml
```
See `docs/DEPLOYMENT_GUIDE_DATABRICKS_APPS.md` for complete guide.

### 4. AWS EC2 / Azure VM
```bash
# Install as systemd service
sudo systemctl enable ot-simulator
sudo systemctl start ot-simulator
```
See `docs/IGNITION_INTEGRATION_GUIDE.md` for cloud deployment.

---

## 🧪 Testing & Development

### Run Tests
```bash
# Install dev dependencies
pip install -r requirements.txt

# Run unit tests
pytest

# Run integration tests
python test_complete_system.py
```

### Code Quality
```bash
# Format code
black opcua2uc/ ot_simulator/

# Type check
mypy opcua2uc/

# Lint
pylint opcua2uc/
```

### Test Configurations
```bash
# Test OPC UA connection
python -m opcua2uc --test-opcua opc.tcp://localhost:4840

# Test MQTT connection
python -m opcua2uc --test-mqtt mqtt://localhost:1883

# Test Zerobus connection
python -m opcua2uc --test-zerobus
```

---

## 📚 Documentation

### Guides
- **VISUALIZATION_STATUS.md** - Advanced visualization roadmap and status
- **SECURITY_IMPLEMENTATION_GUIDE.md** - OPC UA 10101 security setup
- **IGNITION_INTEGRATION_GUIDE.md** - Connect Ignition SCADA
- **PROTOCOLS.md** - Protocol configuration and troubleshooting
- **DEPLOYMENT_GUIDE_DATABRICKS_APPS.md** - Deploy to Databricks Apps
- **NATURAL_LANGUAGE_OPERATOR_GUIDE.md** - NLP operator usage

### Quick Starts
- **QUICK_START_NATURAL_LANGUAGE.md** - 5-minute NLP guide
- **NL_AI_WOT_DEMO_GUIDE.md** - Demo script for NLP + WoT

### Technical
- **NODE_WOT_COMPARISON.md** - Comparison with Node-WoT
- **OPC_UA_10101_WOT_BINDING_RESEARCH.md** - W3C WoT OPC UA binding
- **FFT_FIXES_APPLIED.md** - FFT visualization implementation details

---

## 🔍 Troubleshooting

### Common Issues

**OPC UA Connection Fails**
- Check endpoint URL format: `opc.tcp://hostname:port/path`
- Verify port 4840 is not blocked by firewall
- If security enabled, ensure certificates are trusted

**Simulator Doesn't Start**
- Check port availability: `lsof -i:4840`, `lsof -i:8989`
- Verify config.yaml syntax
- Check logs: `tail -f ot_simulator.log`

**Charts Don't Update**
- Hard refresh browser: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)
- Check WebSocket connection in browser console
- Verify sensors are running: check status cards

**High Memory Usage**
- Reduce number of active charts (< 50 recommended)
- Decrease buffer sizes in config.yaml
- Limit FFT/Spectrogram charts (< 20 recommended)

**Databricks Auth Fails**
- Verify `DBX_CLIENT_ID` and `DBX_CLIENT_SECRET` are set
- Check service principal has permissions on target table
- Test with: `POST /api/databricks/test_auth`

---

## 🤝 Contributing

This is an internal Databricks project. For issues or feature requests:
1. Check existing documentation in the repo
2. Contact the Databricks field engineering team
3. Submit detailed bug reports with logs and configurations

---

## 📄 License

Proprietary - Databricks Inc.

---

## 🎯 Quick Links

- **Live Demo**: http://localhost:8989 (after starting simulator)
- **GitHub**: https://github.com/pravinva/opc-ua-zerobus-connector
- **Databricks**: https://databricks.com/product/iot-analytics

---

**Last Updated**: 2026-01-15
**Version**: 2.0 (with advanced visualizations, NLP, and W3C WoT)
**Maintainer**: Databricks Field Engineering

---

## 🔢 Statistics

- **Total Sensors**: 379 across 16 industries
- **Visualization Code**: 1,356 lines of advanced visualizations
- **Documentation**: 12,000+ lines across 15+ guides
- **Protocols Supported**: 3 (OPC UA, MQTT, Modbus)
- **Security Standards**: OPC UA 10101 compliant
- **W3C WoT TDs**: 379 semantic thing descriptions
- **Update Rate**: 2 Hz (500ms intervals, configurable)
- **Deployment Options**: 4 (local, Docker, Databricks Apps, cloud VMs)
