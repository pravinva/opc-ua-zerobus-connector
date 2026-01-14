# Implementation Priorities: Simulator + Connector

**Date:** January 14, 2026
**Context:** Based on 5 comprehensive research documents (270KB total)
**Goal:** Prioritize top 5 tasks for each branch, implement in parallel

---

## Document Analysis Summary

**Research Documents Analyzed:**

1. **`OPC_UA_10101_WOT_BINDING_RESEARCH.md`** (122KB)
   - OPC UA 10101 WoT Binding specification compliance
   - 4-phase implementation roadmap
   - Gap analysis: Missing TD generation, semantic annotations, enhanced security

2. **`NODE_WOT_VS_DATABRICKS_IOT_CONNECTOR.md`** (52KB)
   - Two-component architecture analysis
   - End-to-end WoT demo flow
   - Benefits: 90% config reduction, semantic queries, auto-discovery

3. **`NODE_WOT_COMPARISON.md`** (28KB)
   - Node-wot vs OT simulator comparison
   - Use node-wot as reference for TD patterns
   - Testing/validation approach

4. **`WHY_NODEJS_VS_PYTHON_FOR_WOT.md`** (33KB)
   - Language choice rationale
   - Python better for Databricks ecosystem
   - Native implementation recommended

5. **`CONVERSATION_SUMMARY.md`** (35KB)
   - All issues resolved (frozen router, favicon, protocol recognition, MQTT headless)
   - Architecture insights
   - Deployment status

---

## 🎯 Top 5 Priorities: Simulator Branch (feature/ot-sim-on-databricks-apps)

### Priority 1: Thing Description Generator (HIGH PRIORITY) ⭐⭐⭐⭐⭐

**Goal:** Generate W3C WoT Thing Descriptions from OPC UA nodes

**Why Critical:**
- Foundation for entire WoT integration
- Enables connector to auto-configure from TD
- Required for OPC UA 10101 compliance
- Blocks all other WoT features

**Effort:** 3-5 days

**Files to Create:**
```
ot_simulator/wot/
├── __init__.py
├── thing_description_generator.py    # Core TD generation logic
├── semantic_mapper.py                # Map sensors → semantic types (SAREF)
└── ontology_loader.py                # Load SAREF, SSN/SOSA ontologies
```

**REST API:**
```python
# Add to enhanced_web_ui.py
@app.get("/api/opcua/thing-description")
async def get_thing_description():
    """Generate W3C WoT Thing Description for OPC UA server.

    Returns JSON-LD with:
    - 379 sensor properties
    - Semantic types (@type: "saref:TemperatureSensor")
    - QUDT unit URIs
    - OPC UA forms (href, nodeId)
    - Security definitions
    """
    generator = ThingDescriptionGenerator(simulator_manager)
    td = await generator.generate_td()
    return td
```

**Key Implementation Details:**
- Map OPC UA variables → WoT properties
- Add semantic annotations: `@type: "saref:TemperatureSensor"`
- Add QUDT unit URIs: `unit: "http://qudt.org/vocab/unit/DEG_C"`
- OPC UA forms: `href: "opc.tcp://localhost:4840"`, `opcua:nodeId: "ns=2;s=mining/..."`
- Security definitions: `"nosec"` (Phase 1), Basic256Sha256 (Phase 2)

**Success Criteria:**
- GET /api/opcua/thing-description returns valid JSON-LD
- All 379 sensors mapped to properties
- Validates against W3C WoT TD schema
- Can be consumed by node-wot client

**Documentation Reference:**
- `OPC_UA_10101_WOT_BINDING_RESEARCH.md` Phase 1 (lines 500-800)
- Code examples provided in document

---

### Priority 2: Semantic Type Annotations (MEDIUM-HIGH PRIORITY) ⭐⭐⭐⭐

**Goal:** Add semantic type annotations to all 379 sensors

**Why Important:**
- Enables semantic queries in Databricks
- Protocol-agnostic sensor identification
- Required for auto-discovery
- Improves metadata richness

**Effort:** 2-3 days

**Files to Modify:**
```
ot_simulator/sensor_models.py          # Add semantic_type field
ot_simulator/wot/semantic_mapper.py    # Map sensor names → SAREF types
```

**Mapping Examples:**
```python
# sensor_models.py
@dataclass
class SensorConfig:
    name: str
    sensor_type: SensorType
    unit: str
    # NEW: Semantic annotations
    semantic_type: str | None = None      # e.g., "saref:TemperatureSensor"
    unit_uri: str | None = None           # e.g., "http://qudt.org/vocab/unit/DEG_C"

# semantic_mapper.py
SEMANTIC_MAPPINGS = {
    # Temperature sensors
    "crusher_1_motor_temperature": "saref:TemperatureSensor",
    "conveyor_belt_temperature": "saref:TemperatureSensor",

    # Power sensors
    "crusher_1_motor_power": "saref:PowerSensor",
    "haul_truck_battery_voltage": "saref:VoltageSensor",

    # Flow sensors
    "pump_flow_rate": "saref:FlowSensor",
    "water_pump_flow": "saref:FlowSensor",

    # Pressure sensors
    "hydraulic_pressure": "saref:PressureSensor",
    "compressor_discharge_pressure": "saref:PressureSensor",
}

UNIT_URI_MAPPINGS = {
    "°C": "http://qudt.org/vocab/unit/DEG_C",
    "kW": "http://qudt.org/vocab/unit/KiloW",
    "m³/h": "http://qudt.org/vocab/unit/M3-PER-HR",
    "bar": "http://qudt.org/vocab/unit/BAR",
    "Hz": "http://qudt.org/vocab/unit/HZ",
    "RPM": "http://qudt.org/vocab/unit/REV-PER-MIN",
}
```

**Success Criteria:**
- All 379 sensors have semantic_type assigned
- All units have QUDT URIs
- Thing Description includes semantic annotations
- Can query: "Find all temperature sensors"

**Documentation Reference:**
- `OPC_UA_10101_WOT_BINDING_RESEARCH.md` Phase 4 (Semantic Enrichment)
- `NODE_WOT_VS_DATABRICKS_IOT_CONNECTOR.md` Section 5 (Real-World Use Case)

---

### Priority 3: Enhanced Security (Basic256Sha256) (MEDIUM PRIORITY) ⭐⭐⭐

**Goal:** Implement OPC UA security policy Basic256Sha256 with certificates

**Why Important:**
- Required for OPC UA 10101 compliance
- Production deployments need security
- Customer requirement for industrial environments
- Thing Description must advertise security

**Effort:** 4-6 days

**Files to Create/Modify:**
```
ot_simulator/security/
├── __init__.py
├── certificate_manager.py       # Generate/load certificates
├── security_policies.py         # Basic256Sha256 configuration
└── user_authentication.py       # Username/password auth

ot_simulator/opcua_simulator.py  # Update security config
```

**Implementation:**
```python
# security_policies.py
from asyncua import ua
from asyncua.crypto import security_policies

class SecurityPolicyManager:
    """Manage OPC UA security policies."""

    async def configure_basic256sha256(self, server):
        """Configure Basic256Sha256 security policy."""
        cert_path = "certs/server_cert.der"
        key_path = "certs/server_key.pem"

        # Generate self-signed cert if not exists
        if not os.path.exists(cert_path):
            await generate_self_signed_certificate(
                cert_path, key_path,
                "Databricks OT Simulator",
                "urn:databricks:ot:simulator"
            )

        # Load certificate
        await server.load_certificate(cert_path)
        await server.load_private_key(key_path)

        # Set security policy
        server.set_security_policy([
            ua.SecurityPolicyType.NoSecurity,
            ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt,
        ])

        # Set security modes
        server.set_security_IDs([
            "Username",
            "Certificate"
        ])
```

**Security Definition in TD:**
```json
{
  "securityDefinitions": {
    "nosec": {
      "scheme": "nosec"
    },
    "basic256sha256": {
      "scheme": "basic",
      "in": "header",
      "description": "OPC UA Basic256Sha256 with X.509 certificates"
    }
  },
  "security": ["basic256sha256"]
}
```

**Success Criteria:**
- OPC UA server accepts Basic256Sha256 connections
- Self-signed certificates auto-generated
- Thing Description advertises security policy
- Backward compatible (NoSecurity still works)

**Documentation Reference:**
- `OPC_UA_10101_WOT_BINDING_RESEARCH.md` Phase 2 (Enhanced Security)

---

### Priority 4: Zero-Bus Push Configuration (MEDIUM PRIORITY) ⭐⭐⭐

**Goal:** Make Zero-Bus push to Databricks configurable and optional

**Why Important:**
- Demo requires streaming to Databricks
- Should be optional (not all users have Zero-Bus)
- Need configuration for workspace, credentials, table
- Enable/disable via config.yaml

**Effort:** 2-3 days

**Files to Create/Modify:**
```
ot_simulator/config.yaml              # Add databricks section
ot_simulator/zerobus_client.py        # NEW: Zero-Bus streaming client
ot_simulator/__main__.py              # Integrate Zero-Bus push
```

**Configuration:**
```yaml
# ot_simulator/config.yaml
databricks:
  enabled: true  # Enable Zero-Bus push
  workspace_host: "https://workspace.cloud.databricks.com"
  zerobus_endpoint: "https://zerobus.cloud.databricks.com"

  auth:
    client_id_env: "DBX_CLIENT_ID"
    client_secret_env: "DBX_CLIENT_SECRET"

  target:
    catalog: "manufacturing"
    schema: "iot_data"
    table: "events_bronze"

  stream:
    max_inflight_records: 1000
    flush_interval_ms: 1000
    batch_size: 50
```

**Implementation:**
```python
# zerobus_client.py
from zerobus.sdk.aio import ZerobusSdk, ZerobusStream

class ZeroBusClient:
    """Stream sensor data to Databricks via Zero-Bus."""

    async def start(self, simulator_manager):
        """Start streaming sensor data."""
        if not self.config.enabled:
            logger.info("Zero-Bus push disabled")
            return

        # Create Zero-Bus stream
        sdk = ZerobusSdk(self.config.zerobus_endpoint, self.config.workspace_host)
        self.stream = await sdk.create_stream(...)

        # Poll sensors and stream
        while self.running:
            for sensor_path in simulator_manager.get_all_sensor_paths():
                value = simulator_manager.get_sensor_value(sensor_path)

                record = {
                    "event_time": int(time.time() * 1_000_000),
                    "sensor_path": sensor_path,
                    "value": value,
                    # Add semantic metadata if available
                    "semantic_type": get_semantic_type(sensor_path),
                    "unit_uri": get_unit_uri(sensor_path),
                }

                await self.stream.ingest_record(record)

            await asyncio.sleep(1.0 / self.config.publish_rate_hz)
```

**Success Criteria:**
- Configurable via config.yaml (enabled: true/false)
- Streams to Databricks Unity Catalog when enabled
- Graceful degradation when disabled (simulator still works)
- Includes semantic metadata in records

**Documentation Reference:**
- `NODE_WOT_VS_DATABRICKS_IOT_CONNECTOR.md` Component 2 (OT Simulator)
- `CONVERSATION_SUMMARY.md` Architecture Insights

---

### Priority 5: Testing & Validation with Node-WoT (LOW-MEDIUM PRIORITY) ⭐⭐

**Goal:** Validate generated Thing Descriptions using node-wot client

**Why Important:**
- Ensures WoT compliance
- Catches TD schema errors
- Validates interoperability
- Demonstrates ecosystem integration

**Effort:** 1-2 days

**Files to Create:**
```
ot_simulator/tests/
├── wot_compliance/
│   ├── package.json              # Node.js dependencies
│   ├── test_td_consumption.js    # Node-wot test client
│   └── validate_td_schema.js     # JSON schema validation
└── test_thing_description.py     # Python tests
```

**Node.js Test Client:**
```javascript
// test_td_consumption.js
const { Servient } = require("@node-wot/core");
const { OpcuaClientFactory } = require("@node-wot/binding-opcua");

async function testTDConsumption() {
  // Fetch TD from simulator
  const tdResponse = await fetch("http://localhost:8000/api/opcua/thing-description");
  const td = await tdResponse.json();

  console.log("✓ Fetched Thing Description");

  // Validate TD schema
  const valid = validateTDSchema(td);
  if (!valid) {
    console.error("✗ TD schema validation failed");
    process.exit(1);
  }
  console.log("✓ TD schema valid");

  // Consume TD with node-wot
  const servient = new Servient();
  servient.addClientFactory(new OpcuaClientFactory());

  const WoT = await servient.start();
  const thing = await WoT.consume(td);

  console.log("✓ TD consumed by node-wot");

  // Test reading a property
  const value = await thing.readProperty("mining/crusher_1_motor_power");
  console.log("✓ Read property:", value);

  // Test observing a property
  thing.observeProperty("utilities/grid_frequency", (data) => {
    console.log("✓ Observed property update:", data);
  });

  console.log("✅ All WoT compliance tests passed!");
}

testTDConsumption();
```

**Success Criteria:**
- Node-wot can fetch and parse our TD
- Node-wot can read OPC UA properties via TD
- Node-wot can observe OPC UA properties
- TD validates against W3C WoT JSON schema
- CI/CD integration (automated tests)

**Documentation Reference:**
- `NODE_WOT_COMPARISON.md` Section "Use Node-WoT for Testing"
- `NODE_WOT_VS_DATABRICKS_IOT_CONNECTOR.md` Phase 3 (Validation Testing)

---

## 🎯 Top 5 Priorities: Connector Branch (main)

### Priority 1: Thing Description Client (HIGH PRIORITY) ⭐⭐⭐⭐⭐

**Goal:** Fetch and parse W3C WoT Thing Descriptions

**Why Critical:**
- Foundation for WoT integration
- Enables auto-configuration from TD
- Required for all other WoT features
- Blocks TD Directory integration

**Effort:** 3-5 days

**Files to Create:**
```
opcua2uc/wot/
├── __init__.py
├── thing_description_client.py   # Fetch & parse TDs
├── thing_config.py               # ThingConfig dataclass
└── wot_bridge.py                 # Bridge TD → ProtocolClient
```

**Implementation:**
```python
# thing_description_client.py
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
        # Extract base URL
        base = td.get("base", "")

        # Parse first property's form to determine protocol
        properties = td.get("properties", {})
        first_prop = next(iter(properties.values()))
        forms = first_prop.get("forms", [])
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

        # Extract semantic types
        semantic_types = {}
        unit_uris = {}
        for prop_name, prop_def in properties.items():
            if "@type" in prop_def:
                semantic_types[prop_name] = prop_def["@type"]
            if "unit" in prop_def:
                unit_uris[prop_name] = prop_def.get("unit")

        return ThingConfig(
            name=td.get("title", "unknown"),
            thing_id=td.get("id"),
            endpoint=base or href,
            protocol_type=protocol_type,
            properties=list(properties.keys()),
            semantic_types=semantic_types,
            unit_uris=unit_uris,
            metadata=td,
        )
```

**REST API:**
```python
# Add to opcua2uc/web_server.py
@app.post("/api/sources/from-td")
async def add_source_from_td(request: dict):
    """Add source from Thing Description URL.

    Request:
    {
      "thing_description": "http://simulator:8000/api/opcua/thing-description",
      "name": "ot-simulator"  # Optional
    }

    Response:
    {
      "name": "ot-simulator",
      "endpoint": "opc.tcp://simulator:4840",
      "protocol_type": "opcua",
      "thing_id": "urn:dev:ops:databricks-ot-simulator",
      "properties": 379,
      "semantic_types": {"mining/crusher_1_motor_power": "saref:PowerSensor", ...}
    }
    """
    td_url = request.get("thing_description")
    td_client = ThingDescriptionClient()
    td = await td_client.fetch_td(td_url)
    thing_config = td_client.parse_td(td)

    # Create ProtocolClient from ThingConfig
    bridge = WoTBridge()
    client = await bridge.create_client_from_td(td_url, on_record_callback)

    # Add to UnifiedBridge
    await unified_bridge.register_client(thing_config.name, client)

    return {
        "name": thing_config.name,
        "endpoint": thing_config.endpoint,
        "protocol_type": thing_config.protocol_type.value,
        "thing_id": thing_config.thing_id,
        "properties": len(thing_config.properties),
        "semantic_types": thing_config.semantic_types,
    }
```

**Success Criteria:**
- Fetch TD from HTTP URL
- Parse TD into ThingConfig
- Detect protocol from TD (OPC-UA, MQTT, Modbus)
- Extract semantic types and unit URIs
- Create ProtocolClient from TD
- POST /api/sources/from-td works end-to-end

**Documentation Reference:**
- `NODE_WOT_VS_DATABRICKS_IOT_CONNECTOR.md` Phase 1 (TD Client)
- Code examples in document

---

### Priority 2: Semantic Metadata in ProtocolRecord (HIGH PRIORITY) ⭐⭐⭐⭐⭐

**Goal:** Extend ProtocolRecord with semantic metadata fields

**Why Critical:**
- Enables semantic queries in Databricks
- Required for Unity Catalog schema extension
- Foundation for protocol-agnostic analytics
- High ROI (enables all downstream benefits)

**Effort:** 2-3 days

**Files to Modify:**
```
opcua2uc/protocols/base.py           # Extend ProtocolRecord
opcua2uc/protocols/opcua_client.py   # Populate semantic fields
opcua2uc/protocols/mqtt_client.py    # Populate semantic fields
opcua2uc/protocols/modbus_client.py  # Populate semantic fields
```

**Implementation:**
```python
# protocols/base.py
@dataclass
class ProtocolRecord:
    """Generic record for any protocol data."""
    # Existing fields
    event_time_ms: int
    source_name: str
    endpoint: str
    protocol_type: ProtocolType
    topic_or_path: str
    value: Any
    value_type: str
    value_num: float | None = None
    metadata: dict[str, Any] | None = None
    status_code: int = 0
    status: str = "Good"

    # NEW: WoT semantic metadata
    thing_id: str | None = None
    thing_title: str | None = None
    semantic_type: str | None = None      # e.g., "saref:TemperatureSensor"
    unit_uri: str | None = None           # e.g., "http://qudt.org/vocab/unit/DEG_C"

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
        if self.thing_title:
            result["thing_title"] = self.thing_title
        if self.semantic_type:
            result["semantic_type"] = self.semantic_type
        if self.unit_uri:
            result["unit_uri"] = self.unit_uri

        return result
```

**WoTBridge Integration:**
```python
# wot/wot_bridge.py
class WoTBridge:
    """Bridge between Thing Descriptions and ProtocolClient."""

    def _wrap_on_record(
        self,
        on_record: Callable[[ProtocolRecord], None],
        thing_config: ThingConfig,
    ) -> Callable[[ProtocolRecord], None]:
        """Wrap on_record to add semantic metadata."""

        def wrapped(record: ProtocolRecord) -> None:
            # Add semantic metadata from TD
            property_name = record.topic_or_path

            record.thing_id = thing_config.thing_id
            record.thing_title = thing_config.name

            # Add semantic type if available
            if property_name in thing_config.semantic_types:
                record.semantic_type = thing_config.semantic_types[property_name]

            # Add unit URI if available
            if property_name in thing_config.unit_uris:
                record.unit_uri = thing_config.unit_uris[property_name]

            on_record(record)

        return wrapped
```

**Success Criteria:**
- ProtocolRecord has semantic fields
- Fields populated when using WoTBridge
- Backward compatible (fields optional)
- Zero-Bus streams include semantic metadata
- Ready for Unity Catalog schema extension

**Documentation Reference:**
- `NODE_WOT_VS_DATABRICKS_IOT_CONNECTOR.md` Phase 2 (Semantic Metadata)

---

### Priority 3: Unity Catalog Schema Extension (MEDIUM-HIGH PRIORITY) ⭐⭐⭐⭐

**Goal:** Extend Unity Catalog table schema with semantic fields

**Why Important:**
- Enables semantic queries in SQL
- Foundation for downstream analytics
- Required for protocol-agnostic ML features
- Demonstrates end-to-end WoT value

**Effort:** 1-2 days (mostly SQL DDL)

**Files to Create:**
```
opcua2uc/sql/
├── create_table_wot.sql          # CREATE TABLE with semantic fields
├── migrate_existing_data.sql     # Migration script (optional)
└── example_queries.sql           # Semantic query examples
```

**SQL Schema:**
```sql
-- create_table_wot.sql
CREATE TABLE IF NOT EXISTS manufacturing.iot_data.events_bronze_wot (
  -- Existing fields
  event_time TIMESTAMP COMMENT 'Event timestamp (microseconds)',
  ingest_time TIMESTAMP COMMENT 'Ingestion timestamp',
  source_name STRING COMMENT 'Source identifier',
  endpoint STRING COMMENT 'Connection endpoint',
  protocol_type STRING COMMENT 'opcua, mqtt, or modbus',
  topic_or_path STRING COMMENT 'Protocol-specific path',
  value STRING COMMENT 'Value as string',
  value_type STRING COMMENT 'Data type',
  value_num DOUBLE COMMENT 'Numeric value (if applicable)',
  metadata MAP<STRING, STRING> COMMENT 'Protocol-specific metadata',
  status_code INT COMMENT 'Quality/status code',
  status STRING COMMENT 'Status description',

  -- NEW: WoT semantic fields
  thing_id STRING COMMENT 'W3C WoT Thing identifier (urn:dev:ops:...)',
  thing_title STRING COMMENT 'Human-readable Thing name',
  semantic_type STRING COMMENT 'Semantic type from ontology (e.g., saref:TemperatureSensor)',
  unit_uri STRING COMMENT 'QUDT unit URI (e.g., http://qudt.org/vocab/unit/DEG_C)'
)
USING DELTA
PARTITIONED BY (DATE(event_time), protocol_type)
COMMENT 'IoT sensor data with W3C WoT semantic metadata';

-- Create view for semantic queries
CREATE OR REPLACE VIEW manufacturing.iot_data.sensors_by_semantic_type AS
SELECT
  semantic_type,
  COUNT(DISTINCT thing_id) as sensor_count,
  COUNT(*) as event_count,
  COLLECT_SET(thing_title) as sensor_names,
  COLLECT_SET(unit_uri) as units
FROM manufacturing.iot_data.events_bronze_wot
WHERE semantic_type IS NOT NULL
GROUP BY semantic_type;

-- Example semantic queries
SELECT * FROM manufacturing.iot_data.events_bronze_wot
WHERE semantic_type = 'saref:TemperatureSensor'
AND value_num > 50;  -- All temps above 50°C

SELECT * FROM manufacturing.iot_data.events_bronze_wot
WHERE semantic_type = 'saref:PowerSensor'
AND DATE(event_time) = CURRENT_DATE();  -- Today's power readings
```

**Configuration Update:**
```yaml
# config.yaml
databricks:
  target:
    catalog: "manufacturing"
    schema: "iot_data"
    table: "events_bronze_wot"  # Use new table with semantic fields
```

**Success Criteria:**
- Table created with semantic fields
- Zero-Bus streams to new table
- Semantic queries work in SQL
- View for sensors_by_semantic_type works
- Documentation for analysts

**Documentation Reference:**
- `NODE_WOT_VS_DATABRICKS_IOT_CONNECTOR.md` Unity Catalog Schema

---

### Priority 4: Auto-Configuration from TD (MEDIUM PRIORITY) ⭐⭐⭐

**Goal:** Auto-configure ProtocolClient directly from Thing Description

**Why Important:**
- Zero manual configuration required
- Demonstrates core WoT value proposition
- 90% reduction in setup time
- Self-documenting sources

**Effort:** 2-3 days

**Files to Modify:**
```
opcua2uc/wot/wot_bridge.py           # Core auto-config logic
opcua2uc/config.py                   # Extend SourceConfig
opcua2uc/web_server.py               # REST API integration
```

**Implementation:**
```python
# wot/wot_bridge.py
class WoTBridge:
    """Bridge between Thing Descriptions and ProtocolClient."""

    async def create_client_from_td(
        self,
        td_url: str,
        on_record: Callable[[ProtocolRecord], None],
        on_stats: Callable[[dict[str, Any]], None] | None = None,
    ) -> ProtocolClient:
        """Create ProtocolClient from Thing Description URL.

        Automatically:
        1. Fetches TD from URL
        2. Parses TD to determine protocol (OPC-UA/MQTT/Modbus)
        3. Extracts endpoint, properties, semantic types
        4. Creates appropriate ProtocolClient
        5. Wraps on_record to add semantic metadata
        """
        # Fetch and parse TD
        td_client = ThingDescriptionClient()
        td = await td_client.fetch_td(td_url)
        thing_config = td_client.parse_td(td)

        # Create protocol-specific config
        config = self._create_protocol_config(thing_config)

        # Create ProtocolClient using existing factory
        from opcua2uc.protocols.factory import create_protocol_client

        client = create_protocol_client(
            protocol_type=thing_config.protocol_type.value,
            source_name=thing_config.name,
            endpoint=thing_config.endpoint,
            config=config,
            on_record=self._wrap_on_record(on_record, thing_config),
            on_stats=on_stats,
        )

        return client

    def _create_protocol_config(self, thing_config: ThingConfig) -> dict:
        """Create protocol-specific config from ThingConfig."""
        config = {
            "thing_id": thing_config.thing_id,
            "semantic_types": thing_config.semantic_types,
            "unit_uris": thing_config.unit_uris,
            "td_metadata": thing_config.metadata,
        }

        # Protocol-specific defaults
        if thing_config.protocol_type == ProtocolType.OPCUA:
            config["variable_limit"] = len(thing_config.properties)
            config["publishing_interval_ms"] = 1000
        elif thing_config.protocol_type == ProtocolType.MQTT:
            # Extract topics from TD forms
            topics = self._extract_mqtt_topics(thing_config)
            config["topics"] = topics
        elif thing_config.protocol_type == ProtocolType.MODBUS:
            # Extract registers from TD metadata
            registers = self._extract_modbus_registers(thing_config)
            config["registers"] = registers

        return config
```

**Before (Manual YAML Config):**
```yaml
sources:
  - name: "ot-simulator"
    endpoint: "opc.tcp://localhost:4840"
    protocol_type: "opcua"
    variable_limit: 379
    publishing_interval_ms: 1000
    reconnect_enabled: true
    # ... 20+ more lines ...
```

**After (TD URL):**
```yaml
sources:
  - name: "ot-simulator"
    thing_description: "http://localhost:8000/api/opcua/thing-description"
    # Done! Auto-configures everything from TD
```

**Success Criteria:**
- Single TD URL auto-configures entire source
- No manual endpoint, protocol, or variable config needed
- Semantic metadata automatically included
- Backward compatible (YAML config still works)

**Documentation Reference:**
- `NODE_WOT_VS_DATABRICKS_IOT_CONNECTOR.md` Configuration Complexity

---

### Priority 5: End-to-End Demo & Documentation (LOW-MEDIUM PRIORITY) ⭐⭐

**Goal:** Create working end-to-end demo and comprehensive documentation

**Why Important:**
- Demonstrates full WoT value proposition
- Enables customer demos
- Onboarding documentation for users
- Validates entire implementation

**Effort:** 2-3 days

**Files to Create:**
```
examples/wot_demo/
├── README.md                      # Quick start guide
├── docker-compose.yml             # Simulator + Connector + Databricks
├── simulator_config.yaml          # Simulator configuration
├── connector_config.yaml          # Connector configuration
└── test_queries.sql               # Example semantic queries

docs/
├── WOT_QUICK_START.md            # 5-minute tutorial
├── WOT_ARCHITECTURE.md           # Architecture deep dive
└── WOT_SEMANTIC_QUERIES.md       # SQL query examples
```

**Docker Compose Setup:**
```yaml
# docker-compose.yml
version: '3.8'

services:
  simulator:
    build: ./ot_simulator
    ports:
      - "4840:4840"  # OPC-UA
      - "8000:8000"  # Web UI + Thing Description
    environment:
      - DATABRICKS_APP_PORT=8000

  connector:
    build: ./opcua2uc
    ports:
      - "8080:8080"  # Connector Web UI
    environment:
      - DBX_CLIENT_ID=${DBX_CLIENT_ID}
      - DBX_CLIENT_SECRET=${DBX_CLIENT_SECRET}
    depends_on:
      - simulator

# Usage:
# 1. Start: docker-compose up
# 2. Get TD: curl http://localhost:8000/api/opcua/thing-description
# 3. Add source: curl -X POST http://localhost:8080/api/sources/from-td \
#                 -d '{"thing_description": "http://simulator:8000/api/opcua/thing-description"}'
# 4. Query Databricks: See test_queries.sql
```

**Quick Start Guide:**
```markdown
# WoT Quick Start (5 Minutes)

## Step 1: Start Simulator
docker-compose up simulator

## Step 2: Verify Thing Description
curl http://localhost:8000/api/opcua/thing-description | jq

## Step 3: Start Connector
docker-compose up connector

## Step 4: Auto-Configure from TD
curl -X POST http://localhost:8080/api/sources/from-td \
  -H "Content-Type: application/json" \
  -d '{"thing_description": "http://simulator:8000/api/opcua/thing-description"}'

## Step 5: Query Databricks
spark.sql("""
  SELECT * FROM manufacturing.iot_data.events_bronze_wot
  WHERE semantic_type = 'saref:TemperatureSensor'
  LIMIT 10
""").show()

## Result: 379 sensors auto-configured in 5 minutes!
```

**Success Criteria:**
- Working docker-compose demo
- 5-minute quick start guide
- Architecture documentation
- Example SQL queries
- Customer-ready demo script

**Documentation Reference:**
- `NODE_WOT_VS_DATABRICKS_IOT_CONNECTOR.md` End-to-End Demo Flow

---

## 📋 Summary Table

### Simulator Branch (feature/ot-sim-on-databricks-apps)

| Priority | Task | Effort | Impact | Blocks |
|----------|------|--------|--------|--------|
| ⭐⭐⭐⭐⭐ | **1. Thing Description Generator** | 3-5 days | 🔥 Critical | All WoT features |
| ⭐⭐⭐⭐ | **2. Semantic Type Annotations** | 2-3 days | 🔥 High | Semantic queries |
| ⭐⭐⭐ | **3. Enhanced Security (Basic256Sha256)** | 4-6 days | ⚠️ Medium | Production use |
| ⭐⭐⭐ | **4. Zero-Bus Push Configuration** | 2-3 days | ⚠️ Medium | Demo requirement |
| ⭐⭐ | **5. Testing with Node-WoT** | 1-2 days | ℹ️ Low | Validation |

**Total Effort:** 12-19 days
**Critical Path:** Priorities 1 & 2 (5-8 days)

### Connector Branch (main)

| Priority | Task | Effort | Impact | Blocks |
|----------|------|--------|--------|--------|
| ⭐⭐⭐⭐⭐ | **1. Thing Description Client** | 3-5 days | 🔥 Critical | All WoT features |
| ⭐⭐⭐⭐⭐ | **2. Semantic Metadata in ProtocolRecord** | 2-3 days | 🔥 Critical | Databricks queries |
| ⭐⭐⭐⭐ | **3. Unity Catalog Schema Extension** | 1-2 days | 🔥 High | Analytics |
| ⭐⭐⭐ | **4. Auto-Configuration from TD** | 2-3 days | ⚠️ Medium | User experience |
| ⭐⭐ | **5. End-to-End Demo & Documentation** | 2-3 days | ℹ️ Low | Customer demos |

**Total Effort:** 10-16 days
**Critical Path:** Priorities 1, 2, 3 (6-10 days)

---

## 🚀 Implementation Strategy

### Phase 1: Foundation (Week 1-2)

**Parallel Work:**
- **Simulator Agent:** Priority 1 (Thing Description Generator)
- **Connector Agent:** Priority 1 (Thing Description Client)

**Goal:** Basic TD generation and consumption working

**Milestone:** Simulator exposes TD → Connector can fetch and parse TD

### Phase 2: Semantic Metadata (Week 2-3)

**Parallel Work:**
- **Simulator Agent:** Priority 2 (Semantic Type Annotations)
- **Connector Agent:** Priority 2 (Semantic Metadata in ProtocolRecord) + Priority 3 (Unity Catalog Schema)

**Goal:** End-to-end semantic metadata flow

**Milestone:** Databricks queries work: `WHERE semantic_type = 'saref:TemperatureSensor'`

### Phase 3: Polish & Production (Week 3-4)

**Parallel Work:**
- **Simulator Agent:** Priority 3 (Enhanced Security) + Priority 4 (Zero-Bus Push)
- **Connector Agent:** Priority 4 (Auto-Configuration) + Priority 5 (Demo & Docs)

**Goal:** Production-ready, customer-demo ready

**Milestone:** Full end-to-end demo, docker-compose working

### Phase 4: Validation (Week 4)

**Sequential Work:**
- **Simulator Agent:** Priority 5 (Node-WoT Testing)
- **Connector Agent:** No additional work

**Goal:** WoT compliance validated

**Milestone:** Node-wot can consume our TDs, CI/CD tests passing

---

## 📊 ROI Justification

**Investment:**
- Simulator: 12-19 developer days
- Connector: 10-16 developer days
- **Total: 22-35 days (~5-7 weeks)**

**Returns:**

1. **Configuration Time Savings**
   - Before: 379 sensors × 10 min = 63 hours
   - After: Single TD URL = 5 minutes
   - **Savings: 62.9 hours per deployment**

2. **Semantic Query Benefits**
   - Protocol-agnostic analytics
   - Faster ML feature engineering
   - Easier data discovery
   - **Value: Impossible to do before, now trivial**

3. **Customer Demo Impact**
   - Professional WoT compliance
   - Industry-standard approach
   - Interoperability story
   - **Value: Competitive differentiation**

4. **Maintenance Reduction**
   - Self-documenting systems
   - Auto-configuration
   - Less manual YAML editing
   - **Savings: ~10 hours/month**

**Annual ROI (100-sensor deployment):**
- Initial setup savings: 62.9 hours = $6,290 (at $100/hr)
- Ongoing maintenance: 10 hrs/month × 12 = 120 hours = $12,000
- **Total annual savings: $18,290**

**Break-even:** 1.2 months for single 100-sensor deployment

---

## Next Steps

1. ✅ Review this implementation plan
2. ✅ Approve priorities and effort estimates
3. 🚀 **Launch subagents in parallel:**
   - Simulator Agent: Priorities 1-5
   - Connector Agent: Priorities 1-5
4. ⏳ Monitor progress (Phases 1-4)
5. ✅ Review & merge when complete

---

**Document Created:** January 14, 2026
**Status:** Ready for Implementation
**Recommendation:** Launch both subagents in parallel to maximize velocity
