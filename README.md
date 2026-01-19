# Databricks IoT Connector & OT Data Simulator

A professional-grade industrial IoT solution combining an edge connector and OT data simulator supporting OPC-UA, MQTT, and Modbus protocols with advanced visualization, natural language control, and W3C WoT integration.

---

## Table of Contents

1. [IoT Edge Connector](#iot-edge-connector)
2. [OT Data Simulator](#ot-data-simulator)
3. [Advanced Visualizations](#advanced-visualizations)
4. [Protocol Browsers](#protocol-browsers)
5. [Natural Language Control](#natural-language-control)
6. [Security](#security)
7. [Local Setup](#local-setup)
8. [Directory Structure](#directory-structure)
9. [Documentation](#documentation)

---

## IoT Edge Connector

The edge connector bridges OT networks with Databricks Unity Catalog, respecting the Purdue Model security architecture.

### Features

- **Multi-Protocol Support**: OPC-UA, MQTT (TLS), Modbus TCP/RTU
- **Zerobus Integration**: Stream to Databricks Unity Catalog via gRPC
- **Automatic Reconnection**: Exponential backoff after network outages
- **Backpressure Handling**: Configurable queue limits and drop policies
- **Rate Limiting**: Prevent overwhelming downstream systems
- **Prometheus Metrics**: Comprehensive monitoring on port 9090
- **Zero Dependencies**: Runs anywhere Docker runs

### Purdue Model Compliant Deployment

The connector respects industrial security architecture (ISA-95/IEC-62443 Purdue Model):

```
┌──────────────────────────────────────────────────────────────────┐
│ Level 5: Enterprise Network (IT)                                │
│                                                                  │
│              ┌──────────────────────┐                            │
│              │   Databricks Cloud   │                            │
│              │   Unity Catalog      │                            │
│              │   Delta Tables       │                            │
│              └──────────▲───────────┘                            │
└─────────────────────────┼────────────────────────────────────────┘
                          │ HTTPS/gRPC (TLS)
┌─────────────────────────┼────────────────────────────────────────┐
│ Level 3.5: DMZ / Edge (Industrial Firewall)                     │
│                          │                                       │
│              ┌───────────▼───────────┐                           │
│              │  IoT Edge Connector   │  ← This Project          │
│              │  (Docker Container)   │                           │
│              │  ┌─────────────────┐  │                           │
│              │  │ OPC UA Client   │  │                           │
│              │  │ MQTT Client     │  │                           │
│              │  │ Modbus Client   │  │                           │
│              │  └─────────────────┘  │                           │
│              │  ┌─────────────────┐  │                           │
│              │  │ Zerobus gRPC    │  │                           │
│              │  │ Buffering/Queue │  │                           │
│              │  └─────────────────┘  │                           │
│              └───────────▲───────────┘                           │
└─────────────────────────┼────────────────────────────────────────┘
                          │ One-way diode (data flows UP only)
┌─────────────────────────┼────────────────────────────────────────┐
│ Level 2: Control Network (OT - Isolated from IT)                │
│                          │                                       │
│    ┌─────────────┐  ┌───▼──────┐  ┌─────────────┐              │
│    │  OPC UA     │  │  MQTT    │  │  Modbus     │              │
│    │  Servers    │  │  Broker  │  │  Devices    │              │
│    │  (PLCs)     │  │ (Sensors)│  │  (RTUs)     │              │
│    └─────────────┘  └──────────┘  └─────────────┘              │
│                                                                  │
│ Level 1: Supervisory Control (SCADA/HMI)                        │
│ Level 0: Field Devices (Physical Processes)                     │
└──────────────────────────────────────────────────────────────────┘
```

**Security Principles**:
- Connector deploys in **DMZ** (Level 3.5), NOT inside plant network (Level 0-2)
- **One-way data flow**: OT → DMZ → Cloud (no commands flow down)
- **Firewall isolation**: OT network remains isolated from IT/Internet
- **Read-only OPC UA/MQTT/Modbus subscriptions** (no writes to PLC)
- **TLS/mTLS**: All cloud communication encrypted
- **No inbound connections**: Connector initiates all connections

### Supported Protocols

#### OPC-UA (OPC Unified Architecture)
- Industrial automation standard
- Subscription-based data change notifications
- Automatic variable discovery
- **Endpoint**: `opc.tcp://hostname:port`

#### MQTT (Message Queuing Telemetry Transport)
- Lightweight pub/sub protocol
- Support for TLS/SSL (mqtts://)
- Wildcard topic subscriptions
- JSON, string, and binary payload parsing
- **Endpoint**: `mqtt://hostname:port` or `mqtts://hostname:port`

#### Modbus (TCP & RTU)
- Master-slave protocol
- Holding/input registers, coils, discrete inputs
- Serial (RTU) and Ethernet (TCP) support
- Configurable scaling and offsets
- **Endpoint**: `modbus://hostname:port` or `modbusrtu:///dev/ttyUSB0`

**Configuration**: Protocol settings are configured in `ot_simulator/config.yaml`. See the inline comments for OPC UA security modes, MQTT TLS settings, and Modbus register mappings.

### Databricks Integration

Data flows through Zerobus (gRPC) to Databricks Unity Catalog:

```yaml
zerobus:
  server_address: "grpc.databricks.com:443"
  oauth_client_id: "${DBX_CLIENT_ID}"
  oauth_client_secret: "${DBX_CLIENT_SECRET}"
  catalog: "manufacturing"
  schema: "iot_data"
  table: "events_bronze"
```

Example configured target: `manufacturing.iot_data.events_bronze`

---

## OT Data Simulator

The simulator generates realistic industrial sensor data for testing and development across 16 industries.

### Features

- **379 Industrial Sensors** across 16 industries (mining, utilities, oil & gas, manufacturing, aerospace, water, space, etc.)
- **Realistic Physics Models**: Temperature, pressure, vibration, flow, power with noise and drift
- **Multi-Protocol Exposure**: OPC UA, MQTT, Modbus, WebSocket
- **Fault Injection**: Simulate equipment failures for testing (spike, drift, freeze, noise)
- **Time-Based Expiration**: Faults automatically reset after configured duration
- **WebSocket Streaming**: Sub-second latency (500ms updates) for real-time visualization
- **Professional Web UI**: Databricks-branded interface with Chart.js 4.4.0

### Simulator Architecture

The OT simulator has a 3-layer architecture that separates data generation, data access, and data exposure:

#### Layer 1: Data Generation (Always Running)
- **SensorSimulator** instances generate realistic industrial sensor data
- 379+ sensors across 16 industries (mining, utilities, renewable energy, manufacturing, etc.)
- Sensors start immediately at startup and run continuously
- **Independent of protocols** - sensors don't "belong to" any specific protocol

#### Layer 2: Data Access (Always Available)
- **SimulatorManager** provides unified access to all sensors
- `get_sensor_value(path)` returns current reading from any sensor
- **Fault injection happens here** - modifies sensor values at the source
- Used by both protocols and WebSocket server

#### Layer 3: Data Exposure (Optional - Controlled by Start/Stop)
- **OPC-UA Simulator**: Network endpoint at `opc.tcp://0.0.0.0:4840`
- **MQTT Simulator**: Publishes to MQTT broker
- **Modbus Simulator**: TCP/RTU endpoint
- **WebSocket Server**: Real-time streaming to browser charts

#### Key Architectural Insights

**Charts vs Protocols:**
- **Charts** get data directly from SimulatorManager via WebSocket (Layer 2)
- **Charts work WITHOUT starting any protocols** - they bypass Layer 3 entirely
- Charts subscribe to specific sensors and receive updates every 500ms

**Protocol Start/Stop:**
- Starting a protocol only creates the **network endpoint** (Layer 3)
- Sensors are always generating data (Layer 1) even when protocols are stopped
- This allows instant chart rendering without waiting for protocol startup

### Supported Industries

**16 Industries, 379 Sensors**:

| Industry | Sensors | Examples |
|----------|---------|----------|
| Mining | 80 | Crusher vibration, conveyor speed, ore temperature |
| Utilities (Power) | 60 | Turbine RPM, generator voltage, transformer temperature |
| Oil & Gas | 50 | Pipeline pressure, flow rate, compressor vibration |
| Manufacturing | 45 | Assembly line speed, motor current, hydraulic pressure |
| Water/Wastewater | 30 | Flow rate, pH, chlorine levels |
| Aerospace | 25 | Turbine temperature, fuel pressure, cabin pressure |
| Renewable Energy | 22 | Wind turbine RPM, solar panel voltage, battery SOC |
| Chemical Processing | 20 | Reactor temperature, distillation column pressure |
| Food & Beverage | 15 | Pasteurizer temperature, bottling line speed |
| Pharmaceuticals | 12 | Bioreactor temperature, clean room pressure |
| Pulp & Paper | 10 | Digester pressure, dryer temperature |
| Metals | 8 | Furnace temperature, rolling mill speed |
| Cement | 6 | Kiln temperature, crusher vibration |
| Space | 4 | Satellite temperature, thruster pressure |
| Textiles | 3 | Loom speed, dye bath temperature |
| Automotive | 9 | Paint booth humidity, assembly torque |

---

## Advanced Visualizations

The simulator provides training-grade visualization capabilities for industrial ML and diagnostics. All visualizations are accessible through the web UI at `http://localhost:8989`.

### 1. FFT Frequency Analysis

- **Use Case**: Bearing fault detection, vibration analysis
- **Technology**: FFT.js 4.0.3, Cooley-Tukey algorithm
- **Features**:
  - 256-point FFT with Hanning window
  - Bearing defect frequency annotations (BPFO, BPFI, BSF, FTF)
  - Toggle between time-domain and frequency-domain views
  - Logarithmic Y-axis for amplitude (g RMS)
- **Access**: Cyan button on vibration sensors

### 2. Multi-Sensor Overlay + Correlation

- **Use Case**: Feature engineering for ML, correlation analysis
- **Features**:
  - Overlay up to 8 sensors on single chart
  - Real-time Pearson correlation coefficients
  - Automatic Y-axis assignment by unit type
  - Dual/triple Y-axis support
- **Access**: Blue multi-select button with Ctrl+Click

### 3. Spectrogram (Time-Frequency Heatmap)

- **Use Case**: Bearing degradation tracking, transient analysis
- **Features**:
  - STFT (Short-Time Fourier Transform) visualization
  - Bubble chart with time vs frequency
  - Tracks 60 FFT computations (30 seconds history)
  - Magnitude shown by bubble size and opacity
- **Access**: Purple button on vibration sensors

### 4. SPC Charts (Statistical Process Control)

- **Use Case**: Manufacturing quality control, Six Sigma compliance
- **Features**:
  - Real-time ±3σ control limits (UCL/LCL)
  - ±2σ warning limits (UWL/LWL)
  - Color-coded points: Blue (in control), Yellow (warning), Red (out of control)
  - 100-sample rolling buffer
- **Access**: Green button on ALL sensors

### 5. Correlation Heatmap Matrix

- **Use Case**: Sensor redundancy analysis, ML feature selection
- **Features**:
  - Pairwise Pearson correlations for all active sensors
  - Color gradient: Red (+1) → Gray (0) → Blue (-1)
  - Interactive tooltips with exact values
  - Dynamic sizing based on sensor count
- **Access**: "Correlation Heatmap" button in overlay section

---

## Protocol Browsers

Two interactive browsers for exploring sensors and Thing Descriptions.

### OPC UA Browser

Interactive hierarchical browser for OPC UA address space:

- **Features**:
  - Tree navigation of namespace hierarchy
  - Real-time value updates
  - Browse by industry, equipment, or sensor type
  - 379 sensors organized in folder structure
- **Access**: Web UI → "OPC UA Browser" tab
- **Endpoint**: `opc.tcp://localhost:4840/ot-simulator/server/`

### W3C WoT Browser

Semantic browser for W3C Web of Things Thing Descriptions:

- **Features**:
  - Filter by industry, semantic type (SAREF/SOSA), or keyword
  - JSON Thing Description download
  - QUDT unit ontology integration
  - Observable properties with min/max ranges
- **Access**: Web UI → "WoT Browser" tab
- **API**: `http://localhost:8989/api/wot/things`

All 379 sensors are exposed as W3C WoT Thing Descriptions with semantic metadata:

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

**Ontologies**:
- SAREF (Smart Appliances REFerence ontology)
- SOSA (Sensor, Observation, Sample, and Actuator ontology)
- QUDT (Quantities, Units, Dimensions, Types units)

---

## Natural Language Control

AI-powered operator interface using Claude Sonnet 4.5 through Databricks Foundation Models.

### Features

- **Conversational Memory**: Remembers context across commands
- **6 Command Categories**:
  - Simulator control (start/stop protocols)
  - Fault injection (simulate equipment failures)
  - Status queries (check running protocols)
  - Sensor discovery (find sensors by industry/type)
  - Protocol management (restart, check endpoints)
  - Conversational (general questions)
- **Databricks Integration**: Uses Foundation Model API
- **Configurable**: Settings in `llm_agent_config.yaml`

### Usage

```bash
# Start Natural Language interface
python -m ot_simulator.llm_agent_operator

You: "start the OPC-UA server"
Agent: OPCUA started
Starting OPC-UA protocol server on port 4840 with 379 sensors...

You: "show me all vibration sensors in mining"
Agent: Found 3 vibration sensors in mining:
  - mining/crusher_1_vibration_x (g)
  - mining/crusher_1_vibration_y (g)
  - mining/vent_fan_1_vibration (g)

You: "inject a fault into the crusher motor for 30 seconds"
Agent: Fault injected into mining/crusher_1_motor_power
Simulating motor overload condition for testing...
```

### Configuration

Edit `ot_simulator/llm_agent_config.yaml`:

```yaml
databricks:
  host: "https://your-workspace.databricks.com"
  endpoint: "/serving-endpoints/databricks-meta-llama-3-1-70b-instruct"

agent:
  model: "databricks-meta-llama-3-1-70b-instruct"
  temperature: 0.7
  max_tokens: 2000
```

---

## Security

### Connector Security

The edge connector implements multiple security layers:

#### OPC UA Security (10101 Compliant)

- **Security Modes**:
  - None (development only)
  - Sign (message integrity)
  - SignAndEncrypt (full security)
- **Security Policies**:
  - Basic256Sha256 (recommended)
  - Aes128_Sha256_RsaOaep
  - Aes256_Sha256_RsaPss
- **Authentication**:
  - Anonymous (development only)
  - Username/Password
  - X.509 Certificate (production)

**Certificate Generation**:
```bash
cd ot_simulator/certs
openssl req -x509 -newkey rsa:2048 -keyout client_key.pem -out client_cert.pem -days 365 -nodes
```

#### MQTT Security

- **TLS/SSL**: mqtts:// endpoints with certificate validation
- **Authentication**: Username/password
- **ACLs**: Topic-level access control (broker-dependent)

#### Modbus Security

- **Network Isolation**: Run on isolated VLAN (OT network)
- **Firewall Rules**: Restrict access to authorized clients
- **No Native Encryption**: Use VPN or IPsec for network-level encryption

#### Databricks Authentication

- **OAuth 2.0 M2M**: Service principal authentication
- **TLS 1.2+**: All gRPC communication encrypted
- **Credential Management**: Environment variables or credential manager

**Environment Variables**:
```bash
export DBX_CLIENT_ID="your-service-principal-client-id"
export DBX_CLIENT_SECRET="your-service-principal-secret"
```

#### Network Security

- **DMZ Deployment**: Connector runs in industrial DMZ (Level 3.5)
- **One-Way Data Flow**: OT → DMZ → Cloud (no commands down)
- **Firewall Isolation**: OT network isolated from Internet
- **No Inbound Connections**: Connector initiates all connections

### Simulator Security

Development simulator includes self-signed certificates for testing:

- **OPC UA**: Basic256Sha256 with certificate authentication
- **MQTT**: TLS support (optional)
- **Web UI**: HTTP (production deployments should use HTTPS reverse proxy)

**Production Recommendations**:
1. Replace self-signed certificates with CA-signed certificates
2. Enable OPC UA SignAndEncrypt mode
3. Use HTTPS reverse proxy for web UI
4. Implement network segmentation
5. Enable audit logging

---

## Local Setup

### Prerequisites

- Python 3.9+ (tested with 3.11, 3.12)
- pip
- Virtual environment (recommended)

### Installation

```bash
# Clone repository
git clone https://github.com/pravinva/opc-ua-zerobus-connector.git
cd opc-ua-zerobus-connector

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running Simulator Only

```bash
# Run simulator with web UI and all protocols
python -m ot_simulator --web-ui --config ot_simulator/config.yaml

# Run simulator with specific protocols
python -m ot_simulator --web-ui --config ot_simulator/config.yaml --protocols opcua mqtt

# Run with Natural Language interface
python -m ot_simulator.llm_agent_operator
```

**Access Points**:
- **Web UI**: http://localhost:8989
- **OPC UA**: opc.tcp://localhost:4840/ot-simulator/server/
- **MQTT**: mqtt://localhost:1883 (if enabled)
- **Modbus TCP**: modbus://localhost:502 (if enabled)
- **Metrics**: http://localhost:9090/metrics (Prometheus)

### Running Connector + Simulator

```bash
# Start full stack (connector + simulator)
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

# Run with custom config
docker run --rm -p 8080:8080 -p 9090:9090 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -e DBX_CLIENT_ID="<your-sp-id>" \
  -e DBX_CLIENT_SECRET="<your-sp-secret>" \
  iot-connector:latest --config /app/config.yaml
```

### Databricks Apps Deployment

```bash
# Deploy to Databricks Apps
./deploy_to_databricks_apps.sh

# Check deployment status
databricks apps get iot-simulator --profile your-profile

# View logs
databricks apps logs iot-simulator --profile your-profile
```

---

## Directory Structure

```
opc-ua-zerobus-connector/
├── databricks_iot_connector/   # Edge connector (production)
│   ├── connector/               # Core connector logic
│   ├── protos/                  # Protocol buffer definitions
│   ├── config/                  # Configuration templates
│   └── certs/                   # TLS certificates
│
├── ot_simulator/                # OT data simulator
│   ├── __main__.py              # Simulator entry point
│   ├── config.yaml              # Simulator configuration
│   ├── sensor_models.py         # 379 sensor definitions
│   ├── simulator_manager.py    # Layer 2: Unified data access
│   ├── opcua_simulator.py       # Layer 3: OPC UA protocol
│   ├── mqtt_simulator.py        # Layer 3: MQTT protocol
│   ├── modbus_simulator.py      # Layer 3: Modbus protocol
│   ├── enhanced_web_ui.py       # Web UI with visualizations
│   ├── websocket_server.py      # Real-time data streaming
│   ├── llm_agent_operator.py    # Natural language control
│   ├── web_ui/                  # Web UI components
│   │   ├── opcua_browser.py     # OPC UA browser
│   │   └── wot_browser.py       # WoT Thing Description browser
│   └── wot/                     # W3C WoT integration
│       ├── thing_description_generator.py
│       └── semantic_mapper.py
│
├── opcua2uc/                    # Connector modules
│   ├── opcua/                   # OPC UA client
│   ├── protocols/               # MQTT, Modbus clients
│   ├── zerobus_producer.py      # Databricks gRPC integration
│   └── web/                     # REST API
│
├── docs/                        # Documentation
│   ├── guides/                  # User guides
│   │   ├── DEPLOYMENT_GUIDE_DATABRICKS_APPS.md
│   │   ├── SECURITY_IMPLEMENTATION_GUIDE.md
│   │   └── OPC_UA_SECURITY_GUIDE.md
│   ├── designs/                 # Architecture designs
│   │   ├── DATABRICKS_APPS_SOLUTION.md
│   │   └── MQTT_BROKER_SOLUTION.md
│   └── research/                # Technical research
│       └── OPC_UA_10101_WOT_BINDING_RESEARCH.md
│
├── tests/                       # Test files
│   ├── test_nl_ai_wot_integration.py
│   └── test_wot_e2e.py
│
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container image
└── deploy_to_databricks_apps.sh # Deployment script
```

### Key Files

- **ot_simulator/config.yaml**: Simulator configuration (protocols, sensors, security)
- **connector_config_databricks_apps.yaml**: Connector configuration (Databricks, protocols)
- **llm_agent_config.yaml**: Natural language agent settings
- **requirements.txt**: Python package dependencies

---

## Documentation

### User Guides

- **Deployment Guide**: `docs/guides/DEPLOYMENT_GUIDE_DATABRICKS_APPS.md`
- **Security Implementation**: `docs/guides/SECURITY_IMPLEMENTATION_GUIDE.md`
- **OPC UA Security**: `docs/guides/OPC_UA_SECURITY_GUIDE.md`
- **Quick Start (Databricks Apps)**: `docs/guides/QUICK_START_DATABRICKS_APPS.md`
- **Ignition Integration**: `docs/guides/IGNITION_INTEGRATION_GUIDE.md`

### Architecture Designs

- **Databricks Apps Solution**: `docs/designs/DATABRICKS_APPS_SOLUTION.md`
- **MQTT Broker Solution**: `docs/designs/MQTT_BROKER_SOLUTION.md`
- **Unity Catalog Schemas**: `docs/designs/UNITY_CATALOG_SCHEMAS.md`

### Research Documents

- **OPC UA 10101 WoT Binding**: `docs/research/OPC_UA_10101_WOT_BINDING_RESEARCH.md`
- **Node-WoT Comparison**: `docs/research/NODE_WOT_COMPARISON.md`
- **Zerobus Networking**: `docs/research/ZEROBUS_NETWORKING_EXPLAINED.md`
- **Python vs Node.js for WoT**: `docs/research/WHY_NODEJS_VS_PYTHON_FOR_WOT.md`

### API Reference

**REST API Endpoints** (port 8989):
- `GET /api/status` - Connector status and metrics
- `GET /api/sources` - List configured sources
- `POST /api/sources` - Add new source (auto-detects protocol)
- `DELETE /api/sources/{name}` - Remove source
- `POST /api/sources/{name}/test` - Test connection
- `GET /api/wot/things` - List all WoT Thing Descriptions
- `GET /api/wot/things/{id}` - Get specific Thing Description
- `POST /api/protocol/detect` - Detect protocol from endpoint

**WebSocket API** (port 8989):
- `ws://localhost:8989/ws` - Real-time sensor data streaming
- Messages: `{"type": "subscribe", "sensor_path": "mining/crusher_1_temperature"}`

**Prometheus Metrics** (port 9090):
- `http://localhost:9090/metrics` - Connector metrics (events, errors, latency)

---

## Troubleshooting

**Common Issues**:
- Connection fails: Check firewall, endpoint, and credentials
- Events dropped: Increase queue size or rate limits
- High memory: Reduce queue size or variable/register counts
- Protocol-specific issues: See inline comments in `ot_simulator/config.yaml`
- Reconnection loops: Check network stability and reconnection settings

**OPC UA Issues**:
- Certificate errors: Regenerate certificates or trust server certificate
- Security policy mismatch: Verify server supports selected policy
- Endpoint not found: Check OPC UA server is running and port is open

**MQTT Issues**:
- TLS handshake fails: Verify CA certificate and hostname match
- Connection refused: Check broker is running and port is open
- Messages not received: Verify topic subscription and QoS level

**Modbus Issues**:
- Timeout errors: Increase timeout or check network latency
- Invalid register address: Verify register address and count
- Device not responding: Check Modbus unit ID and device configuration

**Visualization Issues**:
- FFT button not appearing: Only available on vibration sensors
- Chart data not loading: Ensure WebSocket connection is active
- Correlation heatmap empty: Need at least 2 active charts

---

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## Acknowledgments

- **Databricks**: Unity Catalog, Foundation Models, Apps platform
- **OPC Foundation**: OPC UA specification and Python implementation
- **Eclipse Paho**: MQTT client library
- **pymodbus**: Modbus protocol implementation
- **W3C**: Web of Things specification
- **Chart.js**: Visualization library
- **FFT.js**: Fast Fourier Transform implementation

---

## Contact

For questions, issues, or feature requests, please open an issue on GitHub.
