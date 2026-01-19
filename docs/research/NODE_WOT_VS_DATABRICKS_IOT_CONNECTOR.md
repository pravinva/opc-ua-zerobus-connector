# Node-WoT vs Databricks IoT Connector: WoT Ingestion Analysis

**Date:** January 14, 2026
**Context:** Evaluating whether node-wot or W3C WoT Thing Descriptions could benefit Zero-Bus ingestion architecture

---

## Executive Summary

**Question:** Should we use node-wot for Zero-Bus ingestion of Things? Would W3C WoT Thing Descriptions improve our multi-protocol architecture?

**Answer:**

✅ **YES** - Thing Descriptions would **significantly improve** both components of this project
✅ **YES** - But implement **natively in Python**, not by using node-wot
❌ **NO** - Node-wot itself is not suitable (TypeScript, client-only for OPC-UA/Modbus)

**Project Context:**
This repository contains **TWO complementary components**, both with **Databricks Zero-Bus ingestion** as the main goal:

1. **Databricks IoT Connector** (main branch) - **Production edge client**
   - Reads from customer's OPC-UA servers, MQTT brokers, Modbus devices
   - Multi-protocol client (asyncua, aiomqtt, pymodbus)
   - Streams to Databricks via Zero-Bus gRPC
   - Deployed as Docker container in customer plant network
   - **Purpose:** Production data ingestion

2. **OT Data Simulator** (feature branch: `feature/ot-sim-on-databricks-apps`) - **Demo/testing server**
   - Generates realistic sensor data (379 sensors across 4 industries)
   - Multi-protocol servers (OPC-UA, MQTT, Modbus)
   - Optional Zero-Bus push to Databricks for demos
   - Web UI with real-time charts, LLM chat
   - **Purpose:** Demo, testing, development

**Key Insight:**
Both components have powerful unified protocol abstractions that are **conceptually similar to WoT**, but lack:
- Standard metadata format (Thing Descriptions)
- Semantic annotations
- Discoverable API schemas
- Interoperability with WoT ecosystem

**Recommendation:**
1. **Simulator** (feature branch): Generate Thing Descriptions (already planned in `OPC_UA_10101_WOT_BINDING_RESEARCH.md`)
2. **Connector** (main branch): Consume Thing Descriptions for auto-configuration
3. **End-to-end flow:** Simulator exposes TD → Connector fetches TD → Auto-configures → Streams to Databricks

---

## Two-Component Architecture

This project has **two parallel components** working together for Databricks Zero-Bus ingestion:

### Component 1: Databricks IoT Connector (Main Branch) - Client

**Role:** Production edge data ingestion **client**
**Location:** Customer's plant network (Docker container)
**Direction:** Reads from OT devices → Pushes to Databricks

```
Customer Plant Network                    Databricks Cloud
┌────────────────────────────┐           ┌─────────────────┐
│  OPC-UA Servers            │           │                 │
│  MQTT Brokers              │           │  Unity Catalog  │
│  Modbus Devices            │           │                 │
│  (Real industrial sensors) │           │  Delta Tables   │
└────────┬───────────────────┘           │                 │
         │                               │  Manufacturing  │
         ↓                               │  .iot_data      │
┌────────────────────────────┐           │  .events_bronze │
│  IoT Connector Container   │           │                 │
│  (opcua2uc)                │─────────→ │                 │
│                            │  Zero-Bus │                 │
│  - OPCUAClient             │  gRPC     │                 │
│  - MQTTClient              │           │                 │
│  - ModbusClient            │           │                 │
│  - UnifiedBridge           │           │                 │
│  - ZerobusStreamManager    │           │                 │
└────────────────────────────┘           └─────────────────┘
```

**Key Features:**
- Multi-protocol **clients** (reads from existing servers/brokers)
- Backpressure handling, reconnection logic
- Rate limiting, queue management
- Prometheus metrics, REST API
- Deployed in production environments

### Component 2: OT Data Simulator (Feature Branch) - Server

**Role:** Demo/testing data generator **server**
**Location:** Databricks Apps or local machine
**Direction:** Generates sensor data → Serves via protocols → Optional Zero-Bus push

```
OT Simulator (Databricks Apps)            Databricks Cloud (Same workspace)
┌────────────────────────────┐           ┌─────────────────┐
│  Multi-Protocol Servers    │           │                 │
│                            │           │  Unity Catalog  │
│  - OPC-UA Server (asyncua) │           │                 │
│  - MQTT Publisher (aiomqtt)│           │  Delta Tables   │
│  - Modbus Server (pymodbus)│           │                 │
│                            │           │  Demo data      │
│  379 Sensors:              │           │                 │
│  - Mining (100)            │           │                 │
│  - Utilities (100)         │──────────→│                 │
│  - Manufacturing (89)      │  Optional │                 │
│  - Oil & Gas (90)          │  Zero-Bus │                 │
│                            │  gRPC     │                 │
│  Web UI:                   │           │                 │
│  - Real-time charts        │           │                 │
│  - WebSocket streaming     │           │                 │
│  - LLM natural language    │           │                 │
│  - Fault injection         │           │                 │
└────────────────────────────┘           └─────────────────┘
```

**Key Features:**
- Multi-protocol **servers** (generates and serves data)
- Realistic sensor models (physics-based simulation)
- PLC simulation (IEC 61131-3 programs)
- Web UI with visualization
- LLM natural language control
- Used for demos, testing, development

### End-to-End Demo Flow (Both Components Together)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    End-to-End WoT Demo Architecture                      │
└──────────────────────────────────────────────────────────────────────────┘

Step 1: Simulator Generates Thing Description
┌────────────────────────────────────────────────────┐
│  OT Simulator (feature branch)                     │
│  http://localhost:8000                             │
│                                                    │
│  GET /api/opcua/thing-description                  │
│  ↓                                                 │
│  Returns W3C WoT Thing Description:                │
│  {                                                 │
│    "@context": "...",                              │
│    "id": "urn:dev:ops:databricks-ot-simulator",   │
│    "base": "opc.tcp://localhost:4840",            │
│    "properties": {                                 │
│      "mining/crusher_1_motor_power": {            │
│        "@type": "saref:PowerSensor",              │
│        "unit": "kW",                               │
│        "forms": [...]                              │
│      },                                            │
│      ... (379 sensors)                             │
│    }                                               │
│  }                                                 │
└────────────────────────────────────────────────────┘
                     │
                     │ TD URL
                     ↓
Step 2: Connector Fetches TD and Auto-Configures
┌────────────────────────────────────────────────────┐
│  IoT Connector (main branch)                       │
│  http://localhost:8080                             │
│                                                    │
│  POST /api/sources/from-td                         │
│  {                                                 │
│    "thing_description": "http://localhost:8000/..." │
│  }                                                 │
│  ↓                                                 │
│  WoTBridge:                                        │
│  1. Fetches TD from simulator                      │
│  2. Parses 379 properties                          │
│  3. Detects protocol: OPC-UA                       │
│  4. Creates OPCUAClient                            │
│  5. Subscribes to all 379 sensors                  │
│  6. Adds semantic metadata to records              │
└────────────────────────────────────────────────────┘
                     │
                     │ ProtocolRecords with semantic metadata
                     ↓
Step 3: Zero-Bus Streaming to Databricks
┌────────────────────────────────────────────────────┐
│  ZerobusStreamManager                              │
│                                                    │
│  - Batches records (50 per batch)                  │
│  - Rate limits (500 records/sec)                   │
│  - Handles backpressure                            │
│  - Auto-recovery from errors                       │
│                                                    │
│  gRPC stream to Databricks                         │
└────────────────────────────────────────────────────┘
                     │
                     │ gRPC protobuf messages
                     ↓
Step 4: Unity Catalog with Semantic Metadata
┌────────────────────────────────────────────────────┐
│  Databricks Unity Catalog                          │
│  manufacturing.iot_data.events_bronze_wot         │
│                                                    │
│  Columns:                                          │
│  - event_time: 2026-01-14 12:00:00                │
│  - source_name: "databricks-ot-simulator"         │
│  - protocol_type: "opcua"                         │
│  - topic_or_path: "mining/crusher_1_motor_power" │
│  - value_num: 145.3                                │
│  - thing_id: "urn:dev:ops:databricks-ot-sim..."  │
│  - semantic_type: "saref:PowerSensor"             │
│  - unit_uri: "http://qudt.org/vocab/unit/KiloW"  │
│  - metadata: {...}                                 │
│                                                    │
│  Query all power sensors:                          │
│  SELECT * FROM events_bronze_wot                   │
│  WHERE semantic_type = 'saref:PowerSensor';       │
└────────────────────────────────────────────────────┘
```

**Demo Benefit:**
- **Before WoT:** Manual YAML config with 379 sensor paths, register addresses, topics
- **After WoT:** Single TD URL auto-configures everything + semantic queries in Databricks
- **Time saved:** 379 sensors × 10 min/sensor = 63 hours → 5 minutes

---

## Architecture Comparison

### Current: Databricks IoT Connector (Main Branch)

```
┌────────────────────────────────────────────────────────────┐
│          Databricks IoT Connector (Python)                 │
│                                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │          Unified Bridge (opcua2uc)                 │   │
│  │  - Multi-source orchestration                      │   │
│  │  - Backpressure handling (queue_max_size)         │   │
│  │  - Rate limiting (max_send_records_per_sec)       │   │
│  │  - Automatic reconnection (exponential backoff)   │   │
│  └────────────────────────────────────────────────────┘   │
│           │                                                │
│           ↓                                                │
│  ┌────────────────────────────────────────────────────┐   │
│  │      Protocol Abstraction Layer                    │   │
│  │                                                    │   │
│  │  ┌──────────────────────────────────────────────┐ │   │
│  │  │  ProtocolClient (ABC)                        │ │   │
│  │  │  - connect() / disconnect()                  │ │   │
│  │  │  - subscribe()                               │ │   │
│  │  │  - test_connection()                         │ │   │
│  │  │  - run_with_reconnect()                      │ │   │
│  │  └──────────────────────────────────────────────┘ │   │
│  │           ▲            ▲              ▲            │   │
│  │           │            │              │            │   │
│  │  ┌────────┴───┐  ┌────┴────┐  ┌──────┴──────┐   │   │
│  │  │ OPCUAClient│  │MQTTClient│  │ModbusClient │   │   │
│  │  │            │  │          │  │             │   │   │
│  │  │ - asyncua  │  │ - aiomqtt│  │ - pymodbus  │   │   │
│  │  │ - browse   │  │ - topics │  │ - registers │   │   │
│  │  │ - subscribe│  │ - qos    │  │ - unit_id   │   │   │
│  │  └────────────┘  └──────────┘  └─────────────┘   │   │
│  └────────────────────────────────────────────────────┘   │
│           │                                                │
│           ↓                                                │
│  ┌────────────────────────────────────────────────────┐   │
│  │      Unified Record Format (ProtocolRecord)        │   │
│  │  - event_time_ms                                   │   │
│  │  - source_name                                     │   │
│  │  - endpoint                                        │   │
│  │  - protocol_type (opcua/mqtt/modbus)              │   │
│  │  - topic_or_path                                   │   │
│  │  - value, value_type, value_num                    │   │
│  │  - metadata (dict)                                 │   │
│  │  - status_code, status                             │   │
│  └────────────────────────────────────────────────────┘   │
│           │                                                │
│           ↓                                                │
│  ┌────────────────────────────────────────────────────┐   │
│  │       Zero-Bus Streaming (gRPC)                    │   │
│  │  - ZerobusStreamManager                            │   │
│  │  - Batch ingestion (batch_size: 50)               │   │
│  │  - Rate limiting (token bucket)                    │   │
│  │  - Auto-recovery from stream errors                │   │
│  └────────────────────────────────────────────────────┘   │
│           │                                                │
└───────────┼────────────────────────────────────────────────┘
            ↓
    ┌───────────────────────────────┐
    │  Databricks Unity Catalog     │
    │  manufacturing.iot_data       │
    │  .events_bronze               │
    │                               │
    │  Schema:                      │
    │  - event_time TIMESTAMP       │
    │  - ingest_time TIMESTAMP      │
    │  - source_name STRING         │
    │  - endpoint STRING            │
    │  - protocol_type STRING       │
    │  - topic_or_path STRING       │
    │  - value STRING               │
    │  - value_type STRING          │
    │  - value_num DOUBLE           │
    │  - metadata MAP<STRING,STRING>│
    │  - status_code INT            │
    │  - status STRING              │
    └───────────────────────────────┘
```

### Proposed: WoT-Enhanced Connector

```
┌────────────────────────────────────────────────────────────────┐
│       Databricks IoT Connector + WoT Layer (Python)            │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │         NEW: Thing Description Registry                   │ │
│  │  - Fetch TDs from remote servers (HTTP/local file)       │ │
│  │  - Parse JSON-LD Thing Descriptions                      │ │
│  │  - Auto-configure ProtocolClient from TD                 │ │
│  │  - Semantic query: find by @type, unit, etc.             │ │
│  │  - REST API: GET /api/things                             │ │
│  └──────────────────────────────────────────────────────────┘ │
│           │                                                    │
│           ↓                                                    │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │         NEW: WoT Affordance Mapper                        │ │
│  │  - Map TD properties → ProtocolClient.subscribe()        │ │
│  │  - Map TD actions → ProtocolClient RPC (future)          │ │
│  │  - Map TD events → ProtocolClient subscriptions          │ │
│  │  - Preserve semantic annotations in metadata             │ │
│  └──────────────────────────────────────────────────────────┘ │
│           │                                                    │
│           ↓                                                    │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │      Existing Unified Bridge (opcua2uc)                   │ │
│  │  (No changes required)                                    │ │
│  └──────────────────────────────────────────────────────────┘ │
│           │                                                    │
│           ↓                                                    │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │      Existing Protocol Abstraction Layer                  │ │
│  │  ProtocolClient → OPCUAClient, MQTTClient, ModbusClient  │ │
│  │  (No changes required)                                    │ │
│  └──────────────────────────────────────────────────────────┘ │
│           │                                                    │
│           ↓                                                    │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │      ENHANCED: Unified Record Format                      │ │
│  │  - event_time_ms                                          │ │
│  │  - source_name                                            │ │
│  │  - endpoint                                               │ │
│  │  - protocol_type (opcua/mqtt/modbus)                     │ │
│  │  - topic_or_path                                          │ │
│  │  - value, value_type, value_num                           │ │
│  │  - metadata (dict)                                        │ │
│  │  - status_code, status                                    │ │
│  │  - NEW: semantic_type (e.g., "saref:TemperatureSensor") │ │
│  │  - NEW: unit_uri (e.g., "http://qudt.org/vocab/unit/DEG_C")│
│  │  - NEW: thing_id (TD identifier)                         │ │
│  └──────────────────────────────────────────────────────────┘ │
│           │                                                    │
│           ↓                                                    │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │       Existing Zero-Bus Streaming (gRPC)                  │ │
│  │  (No changes required)                                    │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
            ↓
    ┌───────────────────────────────────┐
    │  Databricks Unity Catalog         │
    │  manufacturing.iot_data           │
    │  .events_bronze_wot               │
    │                                   │
    │  Schema (ENHANCED):               │
    │  - (all existing fields)          │
    │  - semantic_type STRING           │
    │  - unit_uri STRING                │
    │  - thing_id STRING                │
    │  - thing_title STRING             │
    └───────────────────────────────────┘
```

---

## Detailed Comparison

### 1. Protocol Abstraction

| Feature | Node-WoT | Databricks IoT Connector | WoT-Enhanced Connector |
|---------|----------|--------------------------|------------------------|
| **Abstraction Layer** | WoT Thing Description | `ProtocolClient` ABC | Both (TD → ProtocolClient) |
| **Protocol Support** | HTTP, CoAP, MQTT, WS, OPC-UA (client), Modbus (client) | OPC-UA, MQTT, Modbus (all client-mode) | Same + TD-based discovery |
| **Language** | TypeScript/Node.js | Python | Python |
| **Configuration** | JSON-LD Thing Description | YAML config | Both (TD or YAML) |
| **Auto-Discovery** | ✅ Yes (from TD Directory) | ⚠️ Limited (OPC-UA browse only) | ✅ Yes (TD fetch + parse) |
| **Semantic Metadata** | ✅ JSON-LD @context | ❌ No | ✅ Yes (from TD) |

**Winner:** WoT-Enhanced Connector (best of both worlds)

### 2. Configuration Complexity

**Current Databricks IoT Connector (YAML):**
```yaml
sources:
  - name: "plc-1"
    endpoint: "opc.tcp://192.168.1.100:4840"
    protocol_type: "opcua"
    variable_limit: 25
    publishing_interval_ms: 1000
    reconnect_enabled: true
    reconnect_delay_ms: 5000
```

**Proposed WoT-Enhanced Connector:**
```yaml
sources:
  # Option 1: Existing YAML (backward compatible)
  - name: "plc-1"
    endpoint: "opc.tcp://192.168.1.100:4840"
    protocol_type: "opcua"
    variable_limit: 25

  # Option 2: NEW - Reference Thing Description
  - name: "temperature-sensor-1"
    thing_description: "http://192.168.1.50/thing-description"
    # Auto-configures protocol, endpoint, properties from TD!

  # Option 3: NEW - Semantic query
  - name: "all-temperature-sensors"
    thing_directory: "http://td-directory.local"
    semantic_query:
      type: "saref:TemperatureSensor"
      unit: "DegreeCelsius"
    # Discovers all matching Things automatically!
```

**Benefits of WoT Approach:**
- ✅ Auto-configuration from TD (no manual endpoint/protocol setup)
- ✅ Semantic discovery (find all temperature sensors)
- ✅ Self-documenting (TD contains metadata)
- ✅ Backward compatible (existing YAML still works)

### 3. Integration with Databricks

| Feature | Node-WoT | Databricks IoT Connector | WoT-Enhanced Connector |
|---------|----------|--------------------------|------------------------|
| **Zero-Bus Integration** | ❌ No | ✅ Yes (native gRPC) | ✅ Yes (native gRPC) |
| **Unity Catalog** | ❌ No | ✅ Yes | ✅ Yes |
| **Delta Tables** | ❌ No | ✅ Yes (Bronze layer) | ✅ Yes (Bronze + semantic metadata) |
| **Unified Schema** | ❌ No | ✅ ProtocolRecord | ✅ ProtocolRecord + semantic fields |
| **Databricks SDK** | ❌ No | ✅ Yes | ✅ Yes |
| **Service Principal Auth** | ❌ No | ✅ Yes (OAuth M2M) | ✅ Yes (OAuth M2M) |

**Winner:** WoT-Enhanced Connector (adds semantic metadata to existing Databricks integration)

### 4. Multi-Protocol Support

**Current Databricks IoT Connector:**

```python
# protocols/base.py
class ProtocolClient(ABC):
    """Abstract base class for protocol clients."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the protocol endpoint."""
        pass

    @abstractmethod
    async def subscribe(self) -> None:
        """Subscribe to data updates from the protocol endpoint."""
        pass

    @abstractmethod
    async def test_connection(self) -> ProtocolTestResult:
        """Test connectivity without subscribing."""
        pass

    @property
    @abstractmethod
    def protocol_type(self) -> ProtocolType:
        """Return the protocol type."""
        pass
```

**Proposed WoT-Enhanced Connector:**

```python
# wot/thing_description_client.py
class ThingDescriptionClient:
    """Fetch and parse W3C WoT Thing Descriptions."""

    async def fetch_td(self, url: str) -> dict:
        """Fetch Thing Description from HTTP endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            return response.json()

    def parse_td(self, td: dict) -> ThingConfig:
        """Parse TD into ProtocolClient configuration."""
        # Extract base URL
        base = td.get("base", "")

        # Parse first property's form to determine protocol
        properties = td.get("properties", {})
        if not properties:
            raise ValueError("No properties in Thing Description")

        first_prop = next(iter(properties.values()))
        forms = first_prop.get("forms", [])
        if not forms:
            raise ValueError("No forms in property")

        href = forms[0].get("href", "")

        # Detect protocol from href
        if href.startswith("opc.tcp://"):
            protocol_type = ProtocolType.OPCUA
        elif href.startswith("mqtt://") or href.startswith("mqtts://"):
            protocol_type = ProtocolType.MQTT
        elif href.startswith("modbus://"):
            protocol_type = ProtocolType.MODBUS
        else:
            raise ValueError(f"Unsupported protocol in href: {href}")

        # Extract properties to subscribe to
        property_names = list(properties.keys())

        return ThingConfig(
            name=td.get("title", "unknown"),
            thing_id=td.get("id"),
            endpoint=base or href,
            protocol_type=protocol_type,
            properties=property_names,
            semantic_types=self._extract_semantic_types(td),
            metadata=td,
        )

    def _extract_semantic_types(self, td: dict) -> dict[str, str]:
        """Extract semantic @type annotations from TD."""
        types = {}
        for prop_name, prop_def in td.get("properties", {}).items():
            semantic_type = prop_def.get("@type")
            if semantic_type:
                types[prop_name] = semantic_type
        return types
```

**Integration with Existing ProtocolClient:**

```python
# wot/wot_bridge.py
class WoTBridge:
    """Bridge between Thing Descriptions and ProtocolClient."""

    async def create_client_from_td(
        self,
        td_url: str,
        on_record: Callable[[ProtocolRecord], None],
    ) -> ProtocolClient:
        """Create ProtocolClient from Thing Description URL."""

        # Fetch and parse TD
        td_client = ThingDescriptionClient()
        td = await td_client.fetch_td(td_url)
        thing_config = td_client.parse_td(td)

        # Create protocol-specific config
        config = {
            "thing_id": thing_config.thing_id,
            "semantic_types": thing_config.semantic_types,
            "td_metadata": thing_config.metadata,
        }

        # Create ProtocolClient using existing factory
        from opcua2uc.protocols.factory import create_protocol_client

        client = create_protocol_client(
            protocol_type=thing_config.protocol_type,
            source_name=thing_config.name,
            endpoint=thing_config.endpoint,
            config=config,
            on_record=self._wrap_on_record(on_record, thing_config),
        )

        return client

    def _wrap_on_record(
        self,
        on_record: Callable[[ProtocolRecord], None],
        thing_config: ThingConfig,
    ) -> Callable[[ProtocolRecord], None]:
        """Wrap on_record to add semantic metadata."""

        def wrapped(record: ProtocolRecord) -> None:
            # Add semantic metadata from TD
            if record.metadata is None:
                record.metadata = {}

            # Add semantic type if available
            property_name = record.topic_or_path
            if property_name in thing_config.semantic_types:
                record.metadata["semantic_type"] = thing_config.semantic_types[property_name]

            # Add Thing ID
            record.metadata["thing_id"] = thing_config.thing_id
            record.metadata["thing_title"] = thing_config.name

            on_record(record)

        return wrapped
```

### 5. Real-World Use Case: Temperature Monitoring

**Scenario:** Monitor temperature sensors from 3 different vendors:
- **Vendor A:** OPC-UA server (SCADA system)
- **Vendor B:** MQTT broker (wireless sensors)
- **Vendor C:** Modbus TCP device (legacy equipment)

**Current Approach (YAML Configuration):**

```yaml
sources:
  # Vendor A - OPC-UA
  - name: "vendor-a-scada"
    endpoint: "opc.tcp://192.168.1.100:4840"
    protocol_type: "opcua"
    variable_limit: 25
    # Need to manually browse to find temperature variables

  # Vendor B - MQTT
  - name: "vendor-b-wireless"
    endpoint: "mqtt://192.168.1.200:1883"
    protocol_type: "mqtt"
    topics: ["sensors/+/temperature"]
    # Need to know topic structure

  # Vendor C - Modbus
  - name: "vendor-c-legacy"
    endpoint: "modbus://192.168.1.50:502"
    protocol_type: "modbus"
    unit_id: 1
    registers:
      - type: "holding"
        address: 100  # Temperature at register 100
        count: 1
        name: "temperature"
        scale: 0.1  # Need to know scale factor
```

**Problems:**
- ❌ Need to manually determine which OPC-UA variables are temperature
- ❌ Need to know MQTT topic structure
- ❌ Need to know Modbus register addresses and scale factors
- ❌ No semantic understanding that all 3 are temperature sensors
- ❌ Can't query "show me all temperature sensors"

**Proposed WoT-Enhanced Approach:**

```yaml
sources:
  # Option 1: Reference Thing Descriptions directly
  - name: "vendor-a-scada"
    thing_description: "http://192.168.1.100/thing-description"
    # TD auto-specifies:
    # - Protocol: opc.tcp://192.168.1.100:4840
    # - Properties: ["@type": "saref:TemperatureSensor"]
    # - Unit: "http://qudt.org/vocab/unit/DEG_C"

  - name: "vendor-b-wireless"
    thing_description: "http://192.168.1.200/thing-description"
    # TD auto-specifies:
    # - Protocol: mqtt://192.168.1.200:1883
    # - Topics: derived from property forms
    # - Semantic type: saref:TemperatureSensor

  - name: "vendor-c-legacy"
    thing_description: "http://192.168.1.50/thing-description"
    # TD auto-specifies:
    # - Protocol: modbus://192.168.1.50:502
    # - Register: 100, scale: 0.1 (in TD metadata)
    # - Semantic type: saref:TemperatureSensor

  # Option 2: Discover from TD Directory
  - name: "all-temperature-sensors"
    thing_directory: "http://td-directory.local"
    semantic_query:
      type: "saref:TemperatureSensor"
    # Auto-discovers all 3 devices!
```

**Benefits:**
- ✅ Zero manual configuration (TD provides everything)
- ✅ Semantic query: "find all temperature sensors"
- ✅ Unified metadata (all have `semantic_type: "saref:TemperatureSensor"`)
- ✅ Enable advanced queries in Databricks:
  ```sql
  SELECT * FROM iot.sensors.raw_events
  WHERE metadata['semantic_type'] = 'saref:TemperatureSensor'
  AND value_num > 50  -- Find all temps above 50°C
  ```

### 6. Databricks Benefits

**Current Unity Catalog Table:**
```sql
SELECT
  event_time,
  source_name,
  endpoint,
  protocol_type,  -- "opcua", "mqtt", "modbus" (not semantic)
  topic_or_path,  -- Protocol-specific path
  value_num,
  status
FROM manufacturing.iot_data.events_bronze
WHERE source_name = 'vendor-a-scada';
```

**Problems:**
- ❌ Can't query "all temperature sensors" (would need to join with external metadata table)
- ❌ No semantic understanding of what each sensor measures
- ❌ Can't discover relationships between sensors
- ❌ Units are inconsistent (some Celsius, some Fahrenheit, stored as metadata)

**WoT-Enhanced Unity Catalog Table:**
```sql
SELECT
  event_time,
  source_name,
  endpoint,
  protocol_type,        -- "opcua", "mqtt", "modbus"
  topic_or_path,
  value_num,
  status,
  semantic_type,        -- NEW: "saref:TemperatureSensor"
  unit_uri,             -- NEW: "http://qudt.org/vocab/unit/DEG_C"
  thing_id,             -- NEW: "urn:dev:ops:vendor-a-temp-1"
  thing_title           -- NEW: "Vendor A Temperature Sensor"
FROM manufacturing.iot_data.events_bronze_wot
WHERE semantic_type = 'saref:TemperatureSensor';  -- Semantic query!
```

**Benefits:**
- ✅ Semantic queries: "all temperature sensors" regardless of vendor/protocol
- ✅ Unit standardization: QUDT URIs enable automatic conversion
- ✅ Discover relationships: sensors of same @type
- ✅ MLflow integration: use semantic_type for feature engineering
- ✅ Lakehouse Monitoring: monitor by semantic type, not just source

**Example: Advanced Analytics with Semantic Metadata**

```python
# Databricks notebook
from pyspark.sql import functions as F

# Find all sensors measuring flow rate (any protocol)
flow_sensors = (
    spark.table("manufacturing.iot_data.events_bronze_wot")
    .filter(F.col("semantic_type") == "saref:FlowSensor")
)

# Convert all to standard unit (L/min) using QUDT
from qudt import convert_unit

flow_sensors_normalized = flow_sensors.withColumn(
    "flow_L_per_min",
    F.when(
        F.col("unit_uri") == "http://qudt.org/vocab/unit/M3-PER-SEC",
        F.col("value_num") * 60000  # m³/s to L/min
    ).when(
        F.col("unit_uri") == "http://qudt.org/vocab/unit/L-PER-MIN",
        F.col("value_num")  # Already in L/min
    ).otherwise(None)
)

# Now all flow sensors comparable regardless of original unit!
```

---

## Implementation Plan

### Phase 1: Thing Description Client (3-5 days)

**Goal:** Add TD fetching and parsing to databricks-iot-connector

**Files to Create:**
```
opcua2uc/wot/
├── __init__.py
├── thing_description_client.py  # Fetch & parse TDs
├── thing_config.py              # ThingConfig dataclass
└── wot_bridge.py                # Bridge TD → ProtocolClient
```

**Code Example:**

```python
# opcua2uc/wot/thing_description_client.py
from __future__ import annotations

import httpx
from dataclasses import dataclass
from opcua2uc.protocols.base import ProtocolType

@dataclass
class ThingConfig:
    """Configuration extracted from Thing Description."""
    name: str
    thing_id: str
    endpoint: str
    protocol_type: ProtocolType
    properties: list[str]
    semantic_types: dict[str, str]  # property_name → @type
    unit_uris: dict[str, str]       # property_name → unit URI
    metadata: dict

class ThingDescriptionClient:
    """Fetch and parse W3C WoT Thing Descriptions."""

    async def fetch_td(self, url: str) -> dict:
        """Fetch TD from HTTP endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    def parse_td(self, td: dict) -> ThingConfig:
        """Parse TD into ThingConfig."""
        # Implementation from earlier example
        ...
```

**Integration with Existing Config:**

```python
# opcua2uc/config.py (extend existing)
@dataclass
class SourceConfig:
    name: str
    endpoint: str | None = None
    protocol_type: str | None = None

    # NEW: WoT support
    thing_description: str | None = None      # URL to TD
    thing_directory: str | None = None         # TD Directory URL
    semantic_query: dict | None = None         # Query params

    # Existing fields...
    variable_limit: int = 25
    ...
```

**REST API Extensions:**

```python
# Add to opcua2uc/web_server.py

@app.post("/api/sources/from-td")
async def add_source_from_td(request: dict):
    """Add source from Thing Description URL.

    Request:
    {
      "thing_description": "http://192.168.1.100/thing-description",
      "name": "sensor-1"  # Optional, defaults to TD title
    }

    Response:
    {
      "name": "sensor-1",
      "endpoint": "opc.tcp://192.168.1.100:4840",
      "protocol_type": "opcua",
      "thing_id": "urn:dev:ops:sensor-1",
      "properties": ["temperature", "pressure"],
      "semantic_types": {
        "temperature": "saref:TemperatureSensor",
        "pressure": "saref:PressureSensor"
      }
    }
    """
    td_url = request.get("thing_description")
    if not td_url:
        raise ValueError("Missing thing_description URL")

    # Fetch and parse TD
    td_client = ThingDescriptionClient()
    td = await td_client.fetch_td(td_url)
    thing_config = td_client.parse_td(td)

    # Create source config
    source = {
        "name": request.get("name") or thing_config.name,
        "endpoint": thing_config.endpoint,
        "protocol_type": thing_config.protocol_type.value,
        "thing_id": thing_config.thing_id,
        "semantic_types": thing_config.semantic_types,
        "unit_uris": thing_config.unit_uris,
    }

    # Add to configuration
    app_config.sources.append(source)

    # Start source
    await bridge.start_source(source["name"])

    return source
```

### Phase 2: Semantic Metadata in Zero-Bus (2-3 days)

**Goal:** Extend `ProtocolRecord` to include semantic metadata

**Changes to `opcua2uc/protocols/base.py`:**

```python
@dataclass
class ProtocolRecord:
    """Generic record for any protocol data."""
    event_time_ms: int
    source_name: str
    endpoint: str
    protocol_type: ProtocolType

    # Generic fields
    topic_or_path: str
    value: Any
    value_type: str
    value_num: float | None = None

    # Protocol-specific metadata
    metadata: dict[str, Any] | None = None

    # Quality/status
    status_code: int = 0
    status: str = "Good"

    # NEW: WoT semantic metadata
    thing_id: str | None = None
    semantic_type: str | None = None      # e.g., "saref:TemperatureSensor"
    unit_uri: str | None = None           # e.g., "http://qudt.org/vocab/unit/DEG_C"
    thing_title: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "event_time": int(self.event_time_ms) * 1000,
            "ingest_time": int(time.time() * 1_000_000),
            "source_name": self.source_name,
            "endpoint": self.endpoint,
            "protocol_type": self.protocol_type.value,
            "topic_or_path": self.topic_or_path,
            "value": self.value,
            "value_type": self.value_type,
            "value_num": self.value_num,
            "metadata": self.metadata or {},
            "status_code": self.status_code,
            "status": self.status,
        }

        # Add semantic fields if present
        if self.thing_id:
            result["thing_id"] = self.thing_id
        if self.semantic_type:
            result["semantic_type"] = self.semantic_type
        if self.unit_uri:
            result["unit_uri"] = self.unit_uri
        if self.thing_title:
            result["thing_title"] = self.thing_title

        return result
```

**Unity Catalog Table Schema Update:**

```sql
CREATE TABLE IF NOT EXISTS manufacturing.iot_data.events_bronze_wot (
  -- Existing fields
  event_time TIMESTAMP,
  ingest_time TIMESTAMP,
  source_name STRING,
  endpoint STRING,
  protocol_type STRING,
  topic_or_path STRING,
  value STRING,
  value_type STRING,
  value_num DOUBLE,
  metadata MAP<STRING, STRING>,
  status_code INT,
  status STRING,

  -- NEW: WoT semantic fields
  thing_id STRING COMMENT 'W3C WoT Thing identifier (urn:dev:ops:...)',
  semantic_type STRING COMMENT 'Semantic type from ontology (e.g., saref:TemperatureSensor)',
  unit_uri STRING COMMENT 'QUDT unit URI (e.g., http://qudt.org/vocab/unit/DEG_C)',
  thing_title STRING COMMENT 'Human-readable Thing name'
)
USING DELTA
PARTITIONED BY (DATE(event_time), protocol_type);

-- Create view for semantic queries
CREATE OR REPLACE VIEW manufacturing.iot_data.sensors_by_type AS
SELECT
  semantic_type,
  COUNT(DISTINCT thing_id) as sensor_count,
  COUNT(*) as event_count,
  COLLECT_SET(thing_title) as sensor_names
FROM manufacturing.iot_data.events_bronze_wot
WHERE semantic_type IS NOT NULL
GROUP BY semantic_type;
```

### Phase 3: Thing Directory Integration (2-3 days)

**Goal:** Discover Things from TD Directory

**Code Example:**

```python
# opcua2uc/wot/thing_directory_client.py
class ThingDirectoryClient:
    """Client for W3C WoT Thing Directory."""

    def __init__(self, directory_url: str):
        self.directory_url = directory_url.rstrip("/")

    async def search(self, query: dict) -> list[dict]:
        """Search for Things by semantic query.

        Example query:
        {
          "@type": "saref:TemperatureSensor",
          "unit": "DegreeCelsius"
        }
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.directory_url}/search",
                json=query
            )
            response.raise_for_status()
            return response.json()

    async def get_td(self, thing_id: str) -> dict:
        """Get Thing Description by ID."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.directory_url}/things/{thing_id}"
            )
            response.raise_for_status()
            return response.json()
```

**Auto-Discovery Example:**

```python
# opcua2uc/wot/wot_discovery.py
class WoTDiscovery:
    """Auto-discover and configure sources from Thing Directory."""

    async def discover_and_add_sources(
        self,
        directory_url: str,
        semantic_query: dict,
        bridge: UnifiedBridge,
    ) -> list[str]:
        """Discover Things and add as sources.

        Returns list of source names added.
        """
        td_dir = ThingDirectoryClient(directory_url)
        td_client = ThingDescriptionClient()

        # Search directory
        results = await td_dir.search(semantic_query)

        source_names = []
        for thing_summary in results:
            thing_id = thing_summary["id"]

            # Get full TD
            td = await td_dir.get_td(thing_id)

            # Parse TD
            thing_config = td_client.parse_td(td)

            # Add as source
            source = {
                "name": thing_config.name,
                "endpoint": thing_config.endpoint,
                "protocol_type": thing_config.protocol_type.value,
                "thing_id": thing_config.thing_id,
                "semantic_types": thing_config.semantic_types,
            }

            # Add to bridge
            bridge.cfg.sources.append(source)
            await bridge.start_source(source["name"])

            source_names.append(source["name"])

        return source_names
```

**REST API:**

```python
# Add to opcua2uc/web_server.py

@app.post("/api/discovery/auto-add")
async def auto_discover_sources(request: dict):
    """Auto-discover and add sources from Thing Directory.

    Request:
    {
      "thing_directory": "http://td-directory.local",
      "semantic_query": {
        "@type": "saref:TemperatureSensor"
      }
    }

    Response:
    {
      "discovered": 5,
      "added": ["sensor-1", "sensor-2", "sensor-3", "sensor-4", "sensor-5"]
    }
    """
    directory_url = request.get("thing_directory")
    query = request.get("semantic_query", {})

    discovery = WoTDiscovery()
    added = await discovery.discover_and_add_sources(
        directory_url,
        query,
        bridge,
    )

    return {
        "discovered": len(added),
        "added": added
    }
```

### Phase 4: OT Simulator TD Generation (Already Planned!)

**Goal:** Make OT simulator expose Thing Descriptions

**Status:** Already documented in `OPC_UA_10101_WOT_BINDING_RESEARCH.md` Phase 1

**Integration Flow:**

```
┌─────────────────────────────────────────────────────────┐
│              OT Simulator (Branch)                      │
│                                                         │
│  GET http://localhost:8000/api/opcua/thing-description │
│                                                         │
│  Returns TD with 379 sensors:                          │
│  {                                                      │
│    "@context": "https://www.w3.org/2022/wot/td/v1.1",│
│    "id": "urn:dev:ops:databricks-ot-simulator",       │
│    "properties": {                                      │
│      "mining/crusher_1_motor_power": {                 │
│        "@type": "saref:PowerSensor",                   │
│        "type": "number",                                │
│        "unit": "kW",                                    │
│        "forms": [{                                      │
│          "href": "opc.tcp://localhost:4840",           │
│          "opcua:nodeId": "ns=2;s=mining/crusher_1..." │
│        }]                                               │
│      },                                                 │
│      ...                                                │
│    }                                                    │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
            │
            │ Thing Description URL
            ↓
┌─────────────────────────────────────────────────────────┐
│       Databricks IoT Connector (Main Branch)            │
│                                                         │
│  POST /api/sources/from-td                             │
│  {                                                      │
│    "thing_description": "http://localhost:8000/api..."│
│  }                                                      │
│                                                         │
│  → WoT Bridge fetches TD                               │
│  → Parses 379 properties                               │
│  → Creates OPCUAClient                                  │
│  → Subscribes to all sensors                           │
│  → Adds semantic metadata to each record               │
└─────────────────────────────────────────────────────────┘
            │
            │ Zero-Bus gRPC
            ↓
┌─────────────────────────────────────────────────────────┐
│          Databricks Unity Catalog                       │
│                                                         │
│  manufacturing.iot_data.events_bronze_wot              │
│                                                         │
│  Columns:                                               │
│  - thing_id: "urn:dev:ops:databricks-ot-simulator"    │
│  - semantic_type: "saref:PowerSensor"                  │
│  - topic_or_path: "mining/crusher_1_motor_power"      │
│  - value_num: 145.3                                     │
│  - unit_uri: "http://qudt.org/vocab/unit/KiloW"       │
│  - metadata: {...}                                      │
└─────────────────────────────────────────────────────────┘
```

---

## Cost-Benefit Analysis

### Benefits of WoT Integration ✅

**1. Simplified Configuration**
- **Before:** 20+ lines YAML per source (endpoint, protocol, registers, topics, scaling)
- **After:** 2 lines (thing_description URL)
- **Benefit:** 90% reduction in configuration complexity

**2. Semantic Queries**
- **Before:** Can't query "all temperature sensors" across protocols
- **After:** `WHERE semantic_type = 'saref:TemperatureSensor'`
- **Benefit:** Protocol-agnostic analytics

**3. Auto-Discovery**
- **Before:** Manual configuration for each device
- **After:** Semantic query finds all matching devices
- **Benefit:** Scales to 1000s of devices

**4. Unit Standardization**
- **Before:** Mixed units in metadata (string "°C", "degC", "Celsius")
- **After:** QUDT URIs enable automatic conversion
- **Benefit:** Unified analytics, ML feature engineering

**5. Interoperability**
- **Before:** Proprietary ProtocolClient abstraction
- **After:** W3C WoT standard (node-wot, other tools can consume)
- **Benefit:** Ecosystem integration

**6. Self-Documenting**
- **Before:** Need external docs to understand sensors
- **After:** TD contains metadata, units, types
- **Benefit:** Self-service data discovery

### Costs of WoT Integration ⚠️

**1. Development Effort**
- Phase 1: 3-5 days (TD client)
- Phase 2: 2-3 days (semantic metadata)
- Phase 3: 2-3 days (TD directory)
- Phase 4: Already planned (OT simulator TD)
- **Total:** 7-11 days

**2. Backward Compatibility**
- Existing YAML configs must still work
- Need migration guide
- **Mitigation:** Make WoT optional, extend existing config

**3. TD Dependency**
- Devices must provide Thing Descriptions
- Many legacy devices don't have TDs
- **Mitigation:** Keep YAML config as fallback

**4. Testing**
- Need to test TD parsing for all protocols
- Edge cases (malformed TDs, missing fields)
- **Mitigation:** Comprehensive unit tests

### ROI Analysis

**Scenario:** Customer with 100 sensors (50 OPC-UA, 30 MQTT, 20 Modbus)

**Current Approach:**
- Configuration time: 100 sensors × 15 min = 25 hours
- Maintenance: Changes require manual YAML edits
- Analytics: Limited to source-level queries

**WoT-Enhanced Approach:**
- Configuration time: 1 TD Directory query = 5 minutes
- Maintenance: Automatic updates from TD Directory
- Analytics: Semantic queries across all protocols

**Savings:**
- Initial setup: 24.9 hours (99% reduction)
- Ongoing maintenance: ~10 hours/month
- **Annual ROI:** ~140 hours = $14,000 (at $100/hr engineer time)

---

## Comparison with Node-WoT

### What Node-WoT Does Well

1. ✅ **Full W3C WoT compliance** - Reference implementation
2. ✅ **Protocol abstraction** - Clean API for consuming Things
3. ✅ **TD validation** - JSON schema validation
4. ✅ **Multiple bindings** - HTTP, CoAP, MQTT, WS, OPC-UA (client), Modbus (client)
5. ✅ **Active community** - Eclipse Thingweb project

### Why Node-WoT Isn't Suitable for Us

1. ❌ **TypeScript/Node.js** - Our stack is Python/Databricks
2. ❌ **Client-only** - For OPC-UA/Modbus (we need server support in simulator)
3. ❌ **No Zero-Bus integration** - Can't stream to Databricks
4. ❌ **No Unity Catalog** - Can't write to Delta tables
5. ❌ **Runtime overhead** - Would need Node.js in Docker container
6. ❌ **Maintenance burden** - Python ↔ Node.js bridge complexity

### Why Native Python WoT Implementation is Better

1. ✅ **Same language** - Python throughout (opcua2uc, ot_simulator, Databricks SDK)
2. ✅ **Zero-Bus native** - Direct gRPC integration
3. ✅ **Unity Catalog native** - Direct Delta table writes
4. ✅ **Reuse existing code** - ProtocolClient abstraction already excellent
5. ✅ **Lightweight** - Just add TD parsing (no runtime)
6. ✅ **Customizable** - Extend ProtocolRecord with semantic fields
7. ✅ **Testing** - Can use node-wot as validation client (see NODE_WOT_COMPARISON.md)

---

## Conclusion

### Summary

**Should we use node-wot for Zero-Bus ingestion?**

**Answer:** No, but use **W3C WoT Thing Descriptions** as a standard.

**Why:**
- ✅ Thing Descriptions solve real problems (auto-config, semantic queries, interoperability)
- ✅ Databricks IoT Connector has excellent protocol abstraction (`ProtocolClient`)
- ✅ Adding TD support is straightforward (7-11 days)
- ❌ Node-wot itself doesn't fit (TypeScript, client-only, no Zero-Bus)

**Recommended Approach:**

1. **Implement native Python WoT support** in databricks-iot-connector (main branch)
   - Phase 1: Thing Description client (fetch & parse TDs)
   - Phase 2: Extend ProtocolRecord with semantic metadata
   - Phase 3: Thing Directory integration (auto-discovery)

2. **Generate Thing Descriptions** from OT simulator (feature branch)
   - Already documented in `OPC_UA_10101_WOT_BINDING_RESEARCH.md`
   - REST endpoint: `GET /api/opcua/thing-description`

3. **Use node-wot for testing** (optional)
   - Validate our TDs are WoT-compliant
   - See `NODE_WOT_COMPARISON.md` Phase 3

### Key Benefits

1. ✅ **90% reduction in configuration complexity** (TD URL vs 20+ lines YAML)
2. ✅ **Semantic queries** across all protocols (`WHERE semantic_type = 'saref:TemperatureSensor'`)
3. ✅ **Auto-discovery** from Thing Directory (scales to 1000s of devices)
4. ✅ **Unit standardization** (QUDT URIs for ML feature engineering)
5. ✅ **Interoperability** (W3C standard, ecosystem integration)
6. ✅ **Backward compatible** (existing YAML configs still work)

### Next Steps

**Immediate (This Week):**
- [ ] Review this proposal with team
- [ ] Decide if WoT integration is priority
- [ ] Allocate 7-11 developer days

**Short-Term (Next 2 Weeks):**
- [ ] Implement Phase 1 (TD client) in main branch
- [ ] Implement Phase 1 (TD generator) in feature branch
- [ ] Test integration (simulator → connector → Databricks)

**Long-Term (Next Month):**
- [ ] Implement Phase 2 (semantic metadata in Zero-Bus)
- [ ] Implement Phase 3 (TD Directory integration)
- [ ] Customer pilot with WoT-based configuration

---

## References

1. **W3C WoT Thing Description:** https://www.w3.org/TR/wot-thing-description11/
2. **OPC Foundation 10101 (WoT Binding):** https://reference.opcfoundation.org/WoT/Binding/v100/docs/
3. **Eclipse Thingweb node-wot:** https://github.com/eclipse-thingweb/node-wot
4. **SAREF Ontology:** https://saref.etsi.org/core/
5. **QUDT Units:** http://qudt.org/schema/qudt/
6. **Our Research:**
   - `OPC_UA_10101_WOT_BINDING_RESEARCH.md` - OPC UA 10101 compliance roadmap
   - `NODE_WOT_COMPARISON.md` - Node-wot vs OT simulator comparison
7. **Databricks IoT Connector:** Main branch (`opcua2uc/`, `README.md`, `PROTOCOLS.md`)

---

**Document Created:** January 14, 2026
**Status:** Proposal for Review
**Recommendation:** Implement native Python WoT support in databricks-iot-connector
