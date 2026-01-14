# OPC UA 10101: Web of Things Binding - Research & Implementation Guide

**Document Version:** 1.0
**Date:** January 14, 2026
**Author:** Research Analysis
**Status:** 🟡 Implementation Planning

---

## Executive Summary

**OPC UA 10101** is a newly released (January 8, 2026) OPC Foundation companion specification that defines how to expose OPC UA servers through **W3C Web of Things (WoT) Thing Descriptions** in JSON-LD format. This enables simplified integration, cross-protocol interoperability, and web-native access to OT data.

### Current Implementation Status
- ✅ **Strong OPC UA Foundation** - Solid server/client implementation
- ❌ **Missing WoT Layer** - No Thing Description generation
- ⚠️ **Basic Security Only** - NoSecurity mode only
- 🎯 **Compliance Target** - Full OPC UA 10101 compliance recommended

---

## Table of Contents

1. [What is OPC UA 10101 WoT Binding?](#what-is-opc-ua-10101-wot-binding)
2. [Specification Deep Dive](#specification-deep-dive)
3. [Current Implementation Analysis](#current-implementation-analysis)
4. [Gap Analysis](#gap-analysis)
5. [Implementation Roadmap](#implementation-roadmap)
6. [Client-Side Implications](#client-side-implications)
7. [Benefits & Use Cases](#benefits--use-cases)
8. [References & Resources](#references--resources)

---

## What is OPC UA 10101 WoT Binding?

### Overview

OPC UA 10101 bridges two powerful standards:
- **OPC UA** - Industrial automation protocol with rich information modeling
- **W3C WoT** - Web of Things framework for IoT interoperability

### Key Innovation

Instead of requiring OPC UA-specific tools, the binding allows:

**Traditional OPC UA Integration:**
```
Client needs:
1. 50MB+ nodeset XML file
2. OPC UA SDK installation
3. Certificate configuration
4. Custom Browse API implementation
5. Protocol-specific knowledge

Result: High barrier to entry
```

**With OPC UA 10101 WoT Binding:**
```
Client gets:
1. Lightweight JSON-LD Thing Description
2. Standard HTTP/WebSocket access via WoT
3. Machine-readable semantics
4. Cross-protocol compatibility

Result: Web-native, developer-friendly
```

### Core Capabilities

| Feature | Description | Benefit |
|---------|-------------|---------|
| **JSON-LD Thing Descriptions** | W3C standard format for device metadata | Web-native, machine-readable |
| **Selective Node Export** | Export only needed nodes vs entire nodeset | Lighter, faster, focused |
| **Cross-Protocol Integration** | Combine OPC UA with MQTT, HTTP, CoAP | Unified semantic model |
| **Automated Data Mapping** | Machine-readable models for transformations | Shop floor to cloud automation |
| **Modern Security Integration** | OAuth2 + OPC UA authentication | Enterprise-grade security |
| **Semantic Interoperability** | Ontology-based data models | Industry 4.0 ready |

---

## Specification Deep Dive

### 1. Thing Description Structure

A Thing Description (TD) is a JSON-LD document that describes:
- **Metadata** - Identity, title, description
- **Properties** - Data points that can be read/observed/written
- **Actions** - Operations that can be invoked
- **Events** - Notifications that can be subscribed to
- **Links** - Relationships to other Things
- **Security** - Authentication and authorization schemes
- **Forms** - Protocol bindings (how to access via OPC UA)

**Example Thing Description:**

```json
{
  "@context": [
    "https://www.w3.org/2022/wot/td/v1.1",
    {
      "opcua": "http://opcfoundation.org/UA/",
      "saref": "https://saref.etsi.org/core/",
      "xsd": "http://www.w3.org/2001/XMLSchema#"
    }
  ],
  "@type": "Thing",
  "id": "urn:dev:ops:mining-crusher-32473",
  "title": "Mining Crusher #1 Motor",
  "description": "Primary crusher motor power monitoring",
  "securityDefinitions": {
    "nosec": {
      "scheme": "nosec"
    },
    "opcua_channel": {
      "scheme": "OPCUASecurityChannelScheme",
      "securityPolicy": "Basic256Sha256",
      "securityMode": "SignAndEncrypt",
      "in": "header"
    }
  },
  "security": ["nosec"],
  "base": "opc.tcp://0.0.0.0:4840/ot-simulator/server/",
  "properties": {
    "motorPower": {
      "@type": ["saref:PowerSensor", "opcua:AnalogItemType"],
      "title": "Motor Power",
      "description": "Current power consumption of crusher motor",
      "type": "number",
      "unit": "kW",
      "minimum": 0,
      "maximum": 500,
      "observable": true,
      "forms": [{
        "href": "?ns=2;s=mining/crusher_1_motor_power",
        "opcua:nodeId": "ns=2;s=mining/crusher_1_motor_power",
        "opcua:browsePath": "0:Root/0:Objects/2:Mining/2:crusher_1_motor_power",
        "op": ["readproperty", "observeproperty"],
        "contentType": "application/opcua+uadp",
        "subprotocol": "opcua"
      }]
    },
    "motorVibration": {
      "@type": ["saref:Sensor", "opcua:AnalogItemType"],
      "title": "Motor Vibration",
      "type": "number",
      "unit": "mm/s",
      "minimum": 0,
      "maximum": 20,
      "observable": true,
      "forms": [{
        "href": "?ns=2;s=mining/crusher_1_vibration",
        "opcua:nodeId": "ns=2;s=mining/crusher_1_vibration",
        "op": ["readproperty", "observeproperty"]
      }]
    }
  },
  "actions": {
    "resetFaultCounter": {
      "title": "Reset Fault Counter",
      "description": "Reset the fault counter for this motor",
      "forms": [{
        "href": "?ns=2;s=mining/reset_fault_method",
        "opcua:nodeId": "ns=2;s=mining/reset_fault_method",
        "op": "invokeaction"
      }]
    }
  },
  "events": {
    "highVibrationAlert": {
      "title": "High Vibration Alert",
      "description": "Triggered when vibration exceeds threshold",
      "data": {
        "type": "object",
        "properties": {
          "value": {"type": "number"},
          "threshold": {"type": "number"},
          "timestamp": {"type": "string", "format": "date-time"}
        }
      },
      "forms": [{
        "href": "?ns=2;s=mining/vibration_alarm",
        "opcua:nodeId": "ns=2;s=mining/vibration_alarm",
        "op": "subscribeevent"
      }]
    }
  }
}
```

### 2. OPC UA Node to WoT Affordance Mapping

| OPC UA Element | WoT Affordance | Operations | Notes |
|----------------|----------------|------------|-------|
| **Variable (read-only)** | Property | `readproperty`, `observeproperty` | Sensor readings |
| **Variable (writable)** | Property | `readproperty`, `writeproperty`, `observeproperty` | Setpoints, configuration |
| **Method** | Action | `invokeaction` | Commands, control operations |
| **Event/Alarm** | Event | `subscribeevent`, `unsubscribeevent` | Notifications |
| **Object** | Thing or Sub-thing | N/A | Logical grouping |
| **Property** | Property metadata | N/A | Engineering units, ranges |

### 3. Security Schemes (OPC 10101 Specification)

#### NoSecurityScheme
```json
{
  "nosec": {
    "scheme": "nosec",
    "description": "No security - for testing only"
  }
}
```
**Use Case:** Development, testing, internal trusted networks

#### AutoSecurityScheme
```json
{
  "auto": {
    "scheme": "auto",
    "description": "Automatic security negotiation"
  }
}
```
**Use Case:** Client selects strongest mutually supported policy

#### OPCUASecurityChannelScheme
```json
{
  "opcua_channel": {
    "scheme": "OPCUASecurityChannelScheme",
    "securityPolicy": "Basic256Sha256",
    "securityMode": "SignAndEncrypt",
    "in": "header",
    "description": "OPC UA message-level security"
  }
}
```
**Use Case:** Encrypted communication, message integrity

#### OPCUASecurityAuthenticationScheme
```json
{
  "opcua_auth": {
    "scheme": "OPCUASecurityAuthenticationScheme",
    "in": "header",
    "name": "username_password",
    "description": "OPC UA user authentication"
  }
}
```
**Use Case:** User identity, access control

#### OAuth2SecurityScheme
```json
{
  "oauth2": {
    "scheme": "oauth2",
    "flow": "client_credentials",
    "token": "https://auth.example.com/token",
    "scopes": ["read:sensors", "write:actuators"],
    "description": "Modern OAuth2 authentication"
  }
}
```
**Use Case:** Enterprise SSO, token-based auth

### 4. Semantic Annotations

#### SAREF (Smart Applications REFerence ontology)
```json
{
  "@type": ["saref:TemperatureSensor", "opcua:AnalogItemType"],
  "saref:measuresProperty": "saref:Temperature",
  "saref:hasUnit": "qudt:DegreeCelsius"
}
```

#### SSN/SOSA (Semantic Sensor Network)
```json
{
  "@type": ["sosa:Sensor", "opcua:AnalogItemType"],
  "sosa:observes": "ex:CrusherMotorPower",
  "sosa:madeObservation": {
    "@type": "sosa:Observation",
    "sosa:hasResult": {
      "qudt:numericValue": 245.7,
      "qudt:unit": "qudt:Kilowatt"
    }
  }
}
```

#### Industry-Specific Ontologies
```json
{
  "@type": ["industry:MiningEquipment", "opcua:BaseObjectType"],
  "industry:equipmentType": "Crusher",
  "industry:manufacturer": "Metso Outotec",
  "industry:model": "HP500",
  "industry:naicsCode": "212"
}
```

---

## Current Implementation Analysis

### OPC UA Server Implementation (`ot_simulator/opcua_simulator.py`)

#### ✅ Strengths

**1. Solid OPC UA Foundation**
- Uses `asyncua` library (Python async OPC UA implementation)
- Proper namespace management (index 2: `http://databricks.com/iot-simulator`)
- Clean async/await patterns for scalability
- 379 sensors across 16 industries

**2. Rich Node Structure**
```python
# Industry-based hierarchy (Mode 1)
Objects/
  IndustrialSensors/
    Mining/
      crusher_1_motor_power (Variable)
      crusher_1_vibration (Variable)
      conveyor_belt_speed (Variable)
    Utilities/
      generator_1_output_power (Variable)
    [14 more industries...]

# PLC-based hierarchy (Mode 2)
Objects/
  PLCs/
    PLC_MINING (Rockwell ControlLogix 5580)/
      Diagnostics/
        Vendor, Model, RunMode, ScanCycleMs
      Inputs/
        Mining/
          crusher_1_motor_power
```

**3. Comprehensive Metadata**
```python
# Properties attached to each variable
- Unit: "kW", "Hz", "°C", "bar", etc.
- SensorType: "power", "vibration", "temperature", etc.
- MinValue, MaxValue: Engineering ranges
- NominalValue: Normal operating point
- PLCName, PLCVendor, PLCModel: PLC associations
```

**4. Data Type Mappings**
- Sensor values: `ua.VariantType.Double` (float)
- Metadata: `ua.VariantType.String` (str)
- Counters: `ua.VariantType.Int64` (int)
- All standard OPC UA data types properly used

**5. Update Mechanisms**
- 2 Hz update rate (configurable)
- Real-time value generation with realistic simulation
- Fault injection capabilities
- PLC diagnostic counters

#### ❌ Gaps for OPC UA 10101 Compliance

**1. No Thing Description Generation**
- No JSON-LD export capability
- No `@context` definitions
- No WoT affordance mappings
- No REST endpoint for TD retrieval

**2. Basic Security Only**
```python
# Current implementation
self.server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
```
- Only NoSecurity mode
- No certificate management
- No username/password auth
- No encrypted communication

**3. No Semantic Annotations**
- No `@type` annotations on nodes
- No ontology integration (SAREF, SSN)
- No machine-readable semantics beyond basic properties

**4. Limited Discovery**
- Standard OPC UA browse only
- No Thing Description Directory integration
- No automatic TD registration/publication
- No mDNS/Bonjour announcements

**5. No WoT Protocol Bindings**
- No HTTP/WebSocket WoT endpoints
- No CoAP bindings
- Protocol-specific only (OPC UA native)

### OPC UA Client Implementation (`opcua2uc/protocols/opcua_client.py`)

#### ✅ Strengths

**1. Robust Connection Management**
```python
class OPCUAProtocolClient(ProtocolClient):
    """OPC UA client with auto-reconnection."""

    async def connect(self):
        self._client = Client(url=self.endpoint, timeout=self.timeout_s)
        await self._client.connect()
        logger.info(f"Connected to {self.endpoint}")

    async def _reconnect(self):
        """Exponential backoff reconnection."""
        # Implements retry logic with backoff
```

**2. Node Discovery**
```python
async def _discover_variables(self) -> list[Node]:
    """Recursively browse nodes to find variables."""
    objects_node = self._client.nodes.objects
    variables = []

    async def browse_node(node: Node, depth: int = 0):
        if depth > max_depth:
            return

        children = await node.get_children()
        for child in children:
            node_class = await child.read_node_class()
            if node_class == ua.NodeClass.Variable:
                variables.append(child)
            elif node_class == ua.NodeClass.Object:
                await browse_node(child, depth + 1)

    await browse_node(objects_node)
    return variables
```

**3. Data Collection**
```python
async def collect_data(self) -> AsyncIterator[dict]:
    """Stream OPC UA variable values."""
    while self.is_running:
        for node in self.variables:
            try:
                value = await node.read_value()
                data_variant = await node.read_data_value()

                yield {
                    "node_id": node.nodeid.to_string(),
                    "value": value,
                    "status_code": data_variant.StatusCode.value,
                    "timestamp": data_variant.SourceTimestamp,
                    "server_timestamp": data_variant.ServerTimestamp
                }
            except Exception as e:
                logger.error(f"Error reading {node}: {e}")
```

**4. Protobuf Schema**
```protobuf
message OPCUABronzeRecord {
    int64 event_time = 1;           // Microseconds
    int64 ingest_time = 2;          // Microseconds
    string source_name = 3;
    string endpoint = 4;
    int32 namespace = 5;
    string node_id = 6;             // "ns=2;s=mining/crusher_1_motor_power"
    string browse_path = 7;         // "0:Root/0:Objects/2:Mining/..."
    int64 status_code = 8;          // OPC UA status code
    string status = 9;              // "Good", "Bad", etc.
    string value_type = 10;
    string value = 11;
    double value_num = 12;
    bytes raw = 13;
    string plc_name = 14;
    string plc_vendor = 15;
    string plc_model = 16;
}
```

#### ❌ Gaps for OPC UA 10101 Compliance

**1. No Thing Description Consumption**
- Cannot read/parse Thing Descriptions
- No JSON-LD processing
- No automatic endpoint discovery from TD
- No semantic reasoning

**2. No WoT Client Capabilities**
- No HTTP/WebSocket WoT protocol bindings
- Cannot interact via WoT affordances
- Protocol-locked to OPC UA native

**3. Limited Security Options**
```python
# Current: Anonymous connection only
self._client = Client(url=self.endpoint, timeout=self.timeout_s)
await self._client.connect()
```
- No certificate-based auth
- No username/password
- No OAuth2 token support
- NoSecurity mode only

**4. No Semantic Awareness**
- Cannot process `@type` annotations
- No ontology-based filtering
- No semantic queries
- Raw data only

---

## Gap Analysis

### Critical Missing Features (High Priority)

| Feature | Server Impact | Client Impact | Implementation Effort |
|---------|---------------|---------------|----------------------|
| **Thing Description Generation** | Cannot export WoT-compliant metadata | Cannot discover via TD | 3-5 days |
| **Basic256Sha256 Security** | Unencrypted communication | Cannot connect to secure servers | 4-6 days |
| **Certificate Management** | No cert-based auth | No cert-based auth | 2-3 days |
| **TD Directory Integration** | No auto-registration | No TD-based discovery | 2-3 days |

### Important Missing Features (Medium Priority)

| Feature | Server Impact | Client Impact | Implementation Effort |
|---------|---------------|---------------|----------------------|
| **WoT HTTP/WebSocket Bindings** | OPC UA-only access | OPC UA-only access | 5-7 days |
| **Semantic Annotations** | Basic metadata only | No semantic reasoning | 3-4 days |
| **OAuth2 Integration** | No modern enterprise auth | No SSO support | 3-5 days |
| **Username/Password Auth** | Anonymous only | Anonymous only | 2-3 days |

### Nice-to-Have Features (Low Priority)

| Feature | Server Impact | Client Impact | Implementation Effort |
|---------|---------------|---------------|----------------------|
| **Ontology Support (SAREF/SSN)** | Limited semantics | Limited semantics | 3-4 days |
| **Method Call Support** | No actions in TD | Cannot invoke methods via WoT | 2-3 days |
| **Event/Alarm Support** | No events in TD | Cannot subscribe to events via WoT | 3-4 days |
| **mDNS Discovery** | Manual endpoint configuration | Manual endpoint configuration | 2-3 days |

---

## Implementation Roadmap

### Phase 1: Thing Description Layer (Weeks 1-2)

#### Server-Side: TD Generator

**File:** `ot_simulator/opcua_thing_description.py`

```python
class ThingDescriptionGenerator:
    """Generate W3C WoT Thing Descriptions from OPC UA server."""

    def __init__(self, opcua_server, base_url: str):
        self.server = opcua_server
        self.base_url = base_url
        self.namespace_index = 2

    async def generate_td(
        self,
        node_filter: Optional[List[str]] = None,
        include_plc_nodes: bool = True
    ) -> dict:
        """Generate Thing Description.

        Args:
            node_filter: Optional list of node paths to include
            include_plc_nodes: Include PLC hierarchy nodes

        Returns:
            Thing Description as dict (JSON-LD)
        """
        td = {
            "@context": [
                "https://www.w3.org/2022/wot/td/v1.1",
                {
                    "opcua": "http://opcfoundation.org/UA/",
                    "saref": "https://saref.etsi.org/core/",
                    "sosa": "http://www.w3.org/ns/sosa/",
                    "qudt": "http://qudt.org/schema/qudt/",
                    "xsd": "http://www.w3.org/2001/XMLSchema#"
                }
            ],
            "@type": "Thing",
            "id": f"urn:dev:ops:databricks-ot-sim-{uuid.uuid4()}",
            "title": "Databricks OT Data Simulator",
            "description": f"Industrial sensor simulator: {self._get_sensor_count()} sensors across 16 industries",
            "created": datetime.utcnow().isoformat() + "Z",
            "modified": datetime.utcnow().isoformat() + "Z",
            "support": "https://github.com/databricks/ot-simulator",
            "base": self.base_url,
            "securityDefinitions": self._generate_security_definitions(),
            "security": ["nosec"],
            "properties": {},
            "actions": {},
            "events": {}
        }

        # Get filtered nodes
        nodes = await self._get_filtered_nodes(node_filter, include_plc_nodes)

        # Map each node to WoT affordance
        for node in nodes:
            await self._add_node_to_td(td, node)

        return td

    async def _add_node_to_td(self, td: dict, node: Node):
        """Map OPC UA node to WoT affordance."""
        node_class = await node.read_node_class()

        if node_class == ua.NodeClass.Variable:
            property_def = await self._create_property_definition(node)
            sensor_name = self._sanitize_name(property_def['title'])
            td['properties'][sensor_name] = property_def

        elif node_class == ua.NodeClass.Method:
            action_def = await self._create_action_definition(node)
            action_name = self._sanitize_name(action_def['title'])
            td['actions'][action_name] = action_def

    async def _create_property_definition(self, node: Node) -> dict:
        """Create WoT Property from OPC UA Variable."""
        # Read node metadata
        node_id = node.nodeid.to_string()
        display_name = await node.read_display_name()
        description = await node.read_description()
        browse_path = await self._get_browse_path(node)

        # Read custom properties
        unit = await self._read_property(node, "Unit") or ""
        sensor_type = await self._read_property(node, "SensorType") or ""
        min_val = await self._read_property(node, "MinValue")
        max_val = await self._read_property(node, "MaxValue")
        plc_name = await self._read_property(node, "PLCName") or ""

        # Determine operations based on AccessLevel
        access_level = await node.read_attribute(ua.AttributeIds.AccessLevel)
        is_readable = bool(access_level.Value.Value & ua.AccessLevel.CurrentRead)
        is_writable = bool(access_level.Value.Value & ua.AccessLevel.CurrentWrite)

        operations = []
        if is_readable:
            operations.extend(["readproperty", "observeproperty"])
        if is_writable:
            operations.append("writeproperty")

        # Determine semantic type
        semantic_type = self._get_semantic_type(sensor_type)

        property_def = {
            "@type": semantic_type,
            "title": display_name.Text,
            "description": description.Text if description else "",
            "type": "number",  # Most industrial sensors are numeric
            "observable": True,
            "forms": [{
                "href": f"?{node_id}",
                "opcua:nodeId": node_id,
                "opcua:browsePath": browse_path,
                "op": operations,
                "contentType": "application/opcua+uadp",
                "subprotocol": "opcua"
            }]
        }

        # Add optional metadata
        if unit:
            property_def["unit"] = unit
        if min_val is not None:
            property_def["minimum"] = min_val
        if max_val is not None:
            property_def["maximum"] = max_val
        if plc_name:
            property_def["opcua:plcName"] = plc_name

        return property_def

    def _get_semantic_type(self, sensor_type: str) -> List[str]:
        """Map sensor type to semantic ontology types."""
        type_map = {
            "temperature": ["saref:TemperatureSensor", "opcua:AnalogItemType"],
            "pressure": ["saref:PressureSensor", "opcua:AnalogItemType"],
            "power": ["saref:PowerSensor", "opcua:AnalogItemType"],
            "vibration": ["sosa:Sensor", "opcua:AnalogItemType"],
            "flow": ["saref:Sensor", "opcua:AnalogItemType"],
            "level": ["saref:LevelSensor", "opcua:AnalogItemType"]
        }
        return type_map.get(sensor_type, ["opcua:AnalogItemType"])

    def _generate_security_definitions(self) -> dict:
        """Generate security definitions for Thing Description."""
        security_defs = {
            "nosec": {
                "scheme": "nosec",
                "description": "No security - for testing only"
            }
        }

        # Add secure schemes if configured
        if hasattr(self.server, 'security_policy'):
            if self.server.security_policy == "Basic256Sha256":
                security_defs["opcua_channel"] = {
                    "scheme": "OPCUASecurityChannelScheme",
                    "securityPolicy": "Basic256Sha256",
                    "securityMode": "SignAndEncrypt",
                    "in": "header",
                    "description": "OPC UA secure channel with encryption"
                }
                security_defs["opcua_auth"] = {
                    "scheme": "OPCUASecurityAuthenticationScheme",
                    "in": "header",
                    "name": "username_password",
                    "description": "OPC UA user authentication"
                }

        return security_defs

    async def _get_browse_path(self, node: Node) -> str:
        """Get human-readable browse path for node."""
        path_elements = []
        current_node = node

        # Traverse up to root
        while current_node:
            try:
                display_name = await current_node.read_display_name()
                browse_name = await current_node.read_browse_name()

                ns_idx = browse_name.NamespaceIndex
                name = browse_name.Name
                path_elements.insert(0, f"{ns_idx}:{name}")

                # Get parent
                refs = await current_node.get_references(
                    refs=ua.ObjectIds.HierarchicalReferences,
                    direction=ua.BrowseDirection.Inverse
                )
                if refs:
                    current_node = Node(self.server, refs[0].NodeId)
                else:
                    break
            except:
                break

        return "/".join(path_elements)
```

**REST API Endpoint:**

```python
# In ot_simulator/web_ui/api_handlers.py

async def handle_opcua_thing_description(self, request: web.Request) -> web.Response:
    """Export OPC UA server as W3C WoT Thing Description.

    Query Parameters:
        nodes: Optional comma-separated list of node paths to include
        plc: Include PLC hierarchy (true/false, default: true)
        format: Output format (json/jsonld, default: jsonld)

    Returns:
        Thing Description in JSON-LD format
    """
    try:
        # Get query parameters
        node_filter_param = request.query.get('nodes')
        include_plc = request.query.get('plc', 'true').lower() == 'true'
        output_format = request.query.get('format', 'jsonld')

        # Parse node filter
        node_filter = None
        if node_filter_param:
            node_filter = [n.strip() for n in node_filter_param.split(',')]

        # Get OPC UA simulator
        opcua_sim = self.manager.simulators.get('opcua')
        if not opcua_sim:
            return web.json_response(
                {"error": "OPC UA simulator not available"},
                status=503
            )

        # Generate Thing Description
        td_generator = ThingDescriptionGenerator(
            opcua_server=opcua_sim,
            base_url=opcua_sim.config.endpoint
        )

        td = await td_generator.generate_td(
            node_filter=node_filter,
            include_plc_nodes=include_plc
        )

        # Return with appropriate content type
        content_type = "application/td+json" if output_format == "jsonld" else "application/json"

        return web.json_response(
            td,
            content_type=content_type,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Link": '<https://www.w3.org/2022/wot/td/v1.1>; rel="type"'
            }
        )

    except Exception as e:
        logger.exception(f"Error generating Thing Description: {e}")
        return web.json_response(
            {"error": str(e)},
            status=500
        )
```

**Endpoint Usage:**

```bash
# Get full Thing Description (all 379 sensors)
curl http://localhost:8989/api/opcua/thing-description

# Get only mining sensors
curl "http://localhost:8989/api/opcua/thing-description?nodes=mining"

# Get specific sensors
curl "http://localhost:8989/api/opcua/thing-description?nodes=mining/crusher_1_motor_power,utilities/generator_1_output_power"

# Exclude PLC hierarchy
curl "http://localhost:8989/api/opcua/thing-description?plc=false"
```

#### Client-Side: TD Consumer

**File:** `opcua2uc/protocols/opcua_wot_client.py`

```python
class OPCUAWoTClient:
    """OPC UA client with W3C WoT Thing Description support."""

    def __init__(self, td_url: str):
        """Initialize from Thing Description URL.

        Args:
            td_url: URL to Thing Description document or TD itself
        """
        self.td_url = td_url
        self.td: Optional[dict] = None
        self.opcua_client: Optional[OPCUAProtocolClient] = None
        self.properties: Dict[str, dict] = {}
        self.actions: Dict[str, dict] = {}

    async def load_thing_description(self):
        """Load and parse Thing Description."""
        if self.td_url.startswith("http"):
            # Fetch from URL
            async with aiohttp.ClientSession() as session:
                async with session.get(self.td_url) as response:
                    self.td = await response.json()
        else:
            # Load from local file
            with open(self.td_url) as f:
                self.td = json.load(f)

        # Validate TD
        self._validate_td()

        # Extract OPC UA endpoint from base
        base_url = self.td.get('base')
        if not base_url:
            raise ValueError("Thing Description missing 'base' URL")

        # Parse properties and actions
        self.properties = self.td.get('properties', {})
        self.actions = self.td.get('actions', {})

        logger.info(f"Loaded TD: {self.td.get('title')}")
        logger.info(f"  Properties: {len(self.properties)}")
        logger.info(f"  Actions: {len(self.actions)}")

    async def connect(self):
        """Connect to OPC UA server using TD information."""
        if not self.td:
            await self.load_thing_description()

        # Extract endpoint
        base_url = self.td['base']

        # Extract security information
        security_defs = self.td.get('securityDefinitions', {})
        security = self.td.get('security', ['nosec'])

        # Create OPC UA client with appropriate security
        self.opcua_client = OPCUAProtocolClient(
            endpoint=base_url,
            security_config=self._parse_security(security_defs, security)
        )

        await self.opcua_client.connect()
        logger.info(f"Connected to OPC UA server via TD")

    async def read_property(self, property_name: str) -> Any:
        """Read property value using WoT semantics.

        Args:
            property_name: Name of property from Thing Description

        Returns:
            Property value
        """
        if property_name not in self.properties:
            raise ValueError(f"Unknown property: {property_name}")

        prop_def = self.properties[property_name]

        # Extract OPC UA node ID from forms
        forms = prop_def.get('forms', [])
        opcua_form = self._find_opcua_form(forms)

        if not opcua_form:
            raise ValueError(f"No OPC UA form found for property: {property_name}")

        node_id = opcua_form.get('opcua:nodeId')
        if not node_id:
            # Parse from href
            href = opcua_form.get('href', '')
            node_id = href.lstrip('?')

        # Read via OPC UA client
        node = self.opcua_client._client.get_node(node_id)
        value = await node.read_value()

        return value

    async def write_property(self, property_name: str, value: Any):
        """Write property value using WoT semantics."""
        if property_name not in self.properties:
            raise ValueError(f"Unknown property: {property_name}")

        prop_def = self.properties[property_name]

        # Check if writable
        forms = prop_def.get('forms', [])
        opcua_form = self._find_opcua_form(forms)

        if "writeproperty" not in opcua_form.get('op', []):
            raise ValueError(f"Property not writable: {property_name}")

        # Extract node ID
        node_id = opcua_form.get('opcua:nodeId') or opcua_form.get('href', '').lstrip('?')

        # Write via OPC UA client
        node = self.opcua_client._client.get_node(node_id)
        await node.write_value(value)

        logger.info(f"Wrote {value} to {property_name}")

    async def observe_property(
        self,
        property_name: str,
        callback: Callable[[Any], Awaitable[None]]
    ):
        """Subscribe to property changes using WoT semantics.

        Args:
            property_name: Name of property to observe
            callback: Async callback function for value changes
        """
        if property_name not in self.properties:
            raise ValueError(f"Unknown property: {property_name}")

        prop_def = self.properties[property_name]

        # Check if observable
        if not prop_def.get('observable', False):
            raise ValueError(f"Property not observable: {property_name}")

        # Extract node ID
        forms = prop_def.get('forms', [])
        opcua_form = self._find_opcua_form(forms)
        node_id = opcua_form.get('opcua:nodeId') or opcua_form.get('href', '').lstrip('?')

        # Create OPC UA subscription
        node = self.opcua_client._client.get_node(node_id)

        # Create subscription handler
        class SubHandler:
            async def datachange_notification(self, node, val, data):
                await callback(val)

        handler = SubHandler()
        subscription = await self.opcua_client._client.create_subscription(500, handler)
        await subscription.subscribe_data_change(node)

        logger.info(f"Subscribed to {property_name}")

    async def invoke_action(self, action_name: str, input_data: Optional[dict] = None) -> Any:
        """Invoke action using WoT semantics.

        Args:
            action_name: Name of action from Thing Description
            input_data: Optional input parameters

        Returns:
            Action output
        """
        if action_name not in self.actions:
            raise ValueError(f"Unknown action: {action_name}")

        action_def = self.actions[action_name]

        # Extract node ID
        forms = action_def.get('forms', [])
        opcua_form = self._find_opcua_form(forms)
        node_id = opcua_form.get('opcua:nodeId') or opcua_form.get('href', '').lstrip('?')

        # Call OPC UA method
        node = self.opcua_client._client.get_node(node_id)

        # Parse input parameters
        input_args = []
        if input_data:
            input_schema = action_def.get('input', {})
            # Map input_data to OPC UA method arguments
            # (Implementation depends on method signature)

        result = await node.call_method(node_id, *input_args)

        logger.info(f"Invoked action: {action_name}")
        return result

    def _find_opcua_form(self, forms: List[dict]) -> Optional[dict]:
        """Find OPC UA form from list of forms."""
        for form in forms:
            if form.get('subprotocol') == 'opcua':
                return form
        return forms[0] if forms else None

    def _validate_td(self):
        """Validate Thing Description structure."""
        required_fields = ['@context', 'title', 'securityDefinitions', 'security']
        for field in required_fields:
            if field not in self.td:
                raise ValueError(f"Invalid TD: missing '{field}'")

    def _parse_security(self, security_defs: dict, security: List[str]) -> dict:
        """Parse security configuration from TD."""
        # Extract relevant security schemes
        config = {}

        for scheme_name in security:
            if scheme_name in security_defs:
                scheme = security_defs[scheme_name]

                if scheme['scheme'] == 'OPCUASecurityChannelScheme':
                    config['security_policy'] = scheme.get('securityPolicy')
                    config['security_mode'] = scheme.get('securityMode')

                elif scheme['scheme'] == 'OPCUASecurityAuthenticationScheme':
                    config['username'] = scheme.get('username')
                    config['password'] = scheme.get('password')

        return config
```

**Usage Example:**

```python
# Load Thing Description and connect
wot_client = OPCUAWoTClient("http://localhost:8989/api/opcua/thing-description")
await wot_client.connect()

# Read property using WoT semantics
power = await wot_client.read_property("crusher_1_motor_power")
print(f"Motor power: {power} kW")

# Write property
await wot_client.write_property("setpoint_temperature", 75.0)

# Observe property changes
async def on_value_change(value):
    print(f"New value: {value}")

await wot_client.observe_property("crusher_1_vibration", on_value_change)

# Invoke action
await wot_client.invoke_action("resetFaultCounter")
```

---

### Phase 2: Enhanced Security (Weeks 3-4)

#### Certificate Management

**File:** `ot_simulator/opcua_certificates.py`

```python
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta
import ipaddress
from pathlib import Path
import logging

logger = logging.getLogger("ot_simulator.certificates")


class OPCUACertificateManager:
    """Manage OPC UA server and client certificates."""

    def __init__(self, cert_dir: Path = Path("certs")):
        """Initialize certificate manager.

        Args:
            cert_dir: Directory to store certificates
        """
        self.cert_dir = cert_dir
        self.cert_dir.mkdir(exist_ok=True, parents=True)

    async def ensure_certificates(
        self,
        common_name: str = "Databricks OT Simulator",
        organization: str = "Databricks",
        application_uri: str = "urn:databricks:ot-simulator",
        validity_days: int = 365
    ) -> Tuple[Path, Path]:
        """Ensure certificates exist, generate if needed.

        Returns:
            (cert_path, key_path)
        """
        cert_path = self.cert_dir / "server_cert.der"
        key_path = self.cert_dir / "server_key.pem"

        # Check if valid certificates exist
        if cert_path.exists() and key_path.exists():
            if self._is_cert_valid(cert_path):
                logger.info("Using existing certificates")
                return cert_path, key_path
            else:
                logger.warning("Certificates expired, regenerating")

        # Generate new certificates
        logger.info("Generating new self-signed certificates")
        return await self.generate_self_signed_cert(
            common_name=common_name,
            organization=organization,
            application_uri=application_uri,
            validity_days=validity_days
        )

    async def generate_self_signed_cert(
        self,
        common_name: str,
        organization: str,
        application_uri: str,
        validity_days: int = 365
    ) -> Tuple[Path, Path]:
        """Generate self-signed certificate and private key.

        OPC UA requires:
        - RSA 2048+ bit key
        - SHA256 signature
        - SubjectAltName with URI and DNS names
        - KeyUsage: digitalSignature, keyEncipherment, dataEncipherment
        - ExtendedKeyUsage: clientAuth, serverAuth

        Returns:
            (cert_path, key_path)
        """
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        # Create subject/issuer name
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])

        # Create certificate builder
        builder = x509.CertificateBuilder()
        builder = builder.subject_name(subject)
        builder = builder.issuer_name(issuer)
        builder = builder.public_key(private_key.public_key())
        builder = builder.serial_number(x509.random_serial_number())
        builder = builder.not_valid_before(datetime.utcnow())
        builder = builder.not_valid_after(
            datetime.utcnow() + timedelta(days=validity_days)
        )

        # Add SubjectAlternativeName (required for OPC UA)
        builder = builder.add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("ot-simulator"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                x509.IPAddress(ipaddress.IPv4Address("0.0.0.0")),
                x509.UniformResourceIdentifier(application_uri),
            ]),
            critical=False,
        )

        # Add BasicConstraints
        builder = builder.add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )

        # Add KeyUsage (required for OPC UA)
        builder = builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=True,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )

        # Add ExtendedKeyUsage (required for OPC UA)
        builder = builder.add_extension(
            x509.ExtendedKeyUsage([
                x509.ExtendedKeyUsageOID.CLIENT_AUTH,
                x509.ExtendedKeyUsageOID.SERVER_AUTH,
            ]),
            critical=True,
        )

        # Sign certificate
        certificate = builder.sign(private_key, hashes.SHA256())

        # Save certificate (DER format for OPC UA)
        cert_path = self.cert_dir / "server_cert.der"
        with open(cert_path, "wb") as f:
            f.write(certificate.public_bytes(serialization.Encoding.DER))

        # Save private key (PEM format)
        key_path = self.cert_dir / "server_key.pem"
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))

        logger.info(f"Generated certificate: {cert_path}")
        logger.info(f"  Common Name: {common_name}")
        logger.info(f"  Valid until: {certificate.not_valid_after}")

        return cert_path, key_path

    def _is_cert_valid(self, cert_path: Path) -> bool:
        """Check if certificate is still valid."""
        try:
            with open(cert_path, "rb") as f:
                cert_data = f.read()

            cert = x509.load_der_x509_certificate(cert_data)

            # Check expiration
            now = datetime.utcnow()
            if now < cert.not_valid_before or now > cert.not_valid_after:
                return False

            return True
        except Exception as e:
            logger.error(f"Error validating certificate: {e}")
            return False

    async def create_trust_list(self) -> Path:
        """Create trusted certificates list.

        Returns:
            Path to trust list directory
        """
        trust_dir = self.cert_dir / "trusted"
        trust_dir.mkdir(exist_ok=True, parents=True)

        # Copy server cert to trust list (for self-signed)
        server_cert = self.cert_dir / "server_cert.der"
        if server_cert.exists():
            import shutil
            shutil.copy(server_cert, trust_dir / "server_cert.der")

        return trust_dir
```

#### Security Configuration in Server

**Update to:** `ot_simulator/opcua_simulator.py`

```python
async def _configure_security(self):
    """Configure OPC UA security policies and authentication."""
    security_policy = self.config.security_policy

    if security_policy == "NoSecurity":
        # No security (testing only)
        self.server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
        self.server.set_security_IDs(["Anonymous"])
        logger.info("Security: NoSecurity (testing only)")

    elif security_policy == "Basic256Sha256":
        # Generate/load certificates
        cert_manager = OPCUACertificateManager()
        cert_path, key_path = await cert_manager.ensure_certificates(
            common_name=self.config.server_name,
            application_uri=self.config.namespace_uri
        )

        # Load certificates into server
        await self.server.load_certificate(str(cert_path))
        await self.server.load_private_key(str(key_path))

        # Set security policies (from least to most secure)
        self.server.set_security_policy([
            ua.SecurityPolicyType.NoSecurity,
            ua.SecurityPolicyType.Basic256Sha256_Sign,
            ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt,
        ])

        # Create trust list
        trust_dir = await cert_manager.create_trust_list()

        # Set security modes
        self.server.set_security_IDs([
            "Anonymous",
            "Username",
            "Certificate"
        ])

        # Configure user authentication
        if self.config.auth.enabled:
            await self._configure_user_auth()

        logger.info("Security: Basic256Sha256 enabled")
        logger.info(f"  Certificate: {cert_path}")
        logger.info(f"  Trust list: {trust_dir}")

    else:
        raise ValueError(f"Unsupported security policy: {security_policy}")

async def _configure_user_auth(self):
    """Configure username/password authentication."""
    users = self.config.auth.users  # List of {username, password, role}

    for user in users:
        await self.server.user_manager.add_user(
            username=user['username'],
            password=user['password'],
            role=user.get('role', 'user')
        )
        logger.info(f"  Added user: {user['username']} ({user.get('role', 'user')})")
```

#### Configuration Schema

**Update to:** `ot_simulator/config.yaml`

```yaml
opcua:
  enabled: true
  endpoint: "opc.tcp://0.0.0.0:4840/ot-simulator/server/"
  server_name: "Databricks OT Data Simulator"
  namespace_uri: "urn:databricks:ot-simulator"

  # Security configuration
  security_policy: "Basic256Sha256"  # NoSecurity, Basic256Sha256, Aes256_Sha256_RsaPss

  # Authentication
  auth:
    enabled: true
    users:
      - username: "admin"
        password: "admin123"
        role: "admin"
      - username: "operator"
        password: "operator123"
        role: "operator"
      - username: "readonly"
        password: "readonly123"
        role: "viewer"

  # Certificate configuration
  certificates:
    auto_generate: true
    cert_dir: "certs"
    validity_days: 365
    common_name: "Databricks OT Simulator"
    organization: "Databricks"

  # Update frequency
  update_rate_hz: 2.0

  # Which industries to simulate (all 16 industries)
  industries:
    - mining
    - utilities
    # ... (all industries)
```

---

### Phase 3: Thing Description Directory (Week 5)

#### TD Directory Client

**File:** `ot_simulator/opcua_td_directory.py`

```python
import aiohttp
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger("ot_simulator.td_directory")


class ThingDescriptionDirectory:
    """Client for W3C WoT Thing Description Directory.

    Implements: https://w3c.github.io/wot-discovery/
    """

    def __init__(
        self,
        directory_url: str = "http://localhost:8080",
        api_key: Optional[str] = None
    ):
        """Initialize TD Directory client.

        Args:
            directory_url: Base URL of TD Directory server
            api_key: Optional API key for authentication
        """
        self.directory_url = directory_url.rstrip('/')
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self.registration_id: Optional[str] = None

    async def connect(self):
        """Create HTTP session."""
        headers = {}
        if self.api_key:
            headers['Authorization'] = f"Bearer {self.api_key}"

        self.session = aiohttp.ClientSession(headers=headers)
        logger.info(f"Connected to TD Directory: {self.directory_url}")

    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def register_td(self, td: dict) -> str:
        """Register Thing Description with directory.

        Args:
            td: Thing Description document

        Returns:
            Registration ID (URL path)
        """
        if not self.session:
            await self.connect()

        # Validate TD
        if '@context' not in td or 'title' not in td:
            raise ValueError("Invalid Thing Description")

        # POST to /things endpoint
        async with self.session.post(
            f"{self.directory_url}/things",
            json=td,
            headers={"Content-Type": "application/td+json"}
        ) as response:
            if response.status == 201:
                # Extract registration ID from Location header
                location = response.headers.get("Location")
                if not location:
                    # Fallback: extract from response body
                    data = await response.json()
                    location = data.get('id') or data.get('@id')

                self.registration_id = location
                logger.info(f"TD registered: {location}")
                logger.info(f"  Title: {td.get('title')}")
                logger.info(f"  ID: {td.get('id')}")

                return location

            elif response.status == 409:
                # Conflict: TD already exists
                error = await response.text()
                logger.warning(f"TD already registered: {error}")
                raise ValueError(f"TD conflict: {error}")

            else:
                error = await response.text()
                raise Exception(f"TD registration failed ({response.status}): {error}")

    async def update_td(self, td_id: str, td: dict) -> bool:
        """Update existing Thing Description.

        Args:
            td_id: Registration ID
            td: Updated Thing Description

        Returns:
            True if successful
        """
        if not self.session:
            await self.connect()

        # PUT to /things/{id} endpoint
        async with self.session.put(
            f"{self.directory_url}/things/{td_id}",
            json=td,
            headers={"Content-Type": "application/td+json"}
        ) as response:
            if response.status == 204:
                logger.info(f"TD updated: {td_id}")
                return True
            else:
                error = await response.text()
                raise Exception(f"TD update failed ({response.status}): {error}")

    async def unregister_td(self, td_id: Optional[str] = None) -> bool:
        """Remove Thing Description from directory.

        Args:
            td_id: Registration ID (uses self.registration_id if not provided)

        Returns:
            True if successful
        """
        if not self.session:
            await self.connect()

        td_id = td_id or self.registration_id
        if not td_id:
            raise ValueError("No registration ID provided")

        # DELETE /things/{id} endpoint
        async with self.session.delete(
            f"{self.directory_url}/things/{td_id}"
        ) as response:
            if response.status == 204:
                logger.info(f"TD unregistered: {td_id}")
                self.registration_id = None
                return True
            elif response.status == 404:
                logger.warning(f"TD not found: {td_id}")
                return False
            else:
                error = await response.text()
                raise Exception(f"TD unregister failed ({response.status}): {error}")

    async def search_td(
        self,
        query: Optional[str] = None,
        type_filter: Optional[List[str]] = None,
        location: Optional[Dict[str, float]] = None
    ) -> List[dict]:
        """Search Thing Descriptions in directory.

        Args:
            query: Text search query
            type_filter: Filter by @type (e.g., ["saref:TemperatureSensor"])
            location: Geo-location filter {lat, lon, radius_km}

        Returns:
            List of matching Thing Descriptions
        """
        if not self.session:
            await self.connect()

        # Build query parameters
        params = {}
        if query:
            params['q'] = query
        if type_filter:
            params['type'] = ','.join(type_filter)
        if location:
            params['lat'] = location.get('lat')
            params['lon'] = location.get('lon')
            params['radius'] = location.get('radius_km', 10)

        # GET /search endpoint
        async with self.session.get(
            f"{self.directory_url}/search",
            params=params
        ) as response:
            if response.status == 200:
                results = await response.json()
                logger.info(f"Search returned {len(results)} results")
                return results
            else:
                error = await response.text()
                raise Exception(f"Search failed ({response.status}): {error}")

    async def get_td(self, td_id: str) -> dict:
        """Retrieve Thing Description by ID.

        Args:
            td_id: Registration ID

        Returns:
            Thing Description document
        """
        if not self.session:
            await self.connect()

        # GET /things/{id} endpoint
        async with self.session.get(
            f"{self.directory_url}/things/{td_id}"
        ) as response:
            if response.status == 200:
                td = await response.json()
                return td
            elif response.status == 404:
                raise ValueError(f"TD not found: {td_id}")
            else:
                error = await response.text()
                raise Exception(f"Get TD failed ({response.status}): {error}")

    async def list_all_tds(self, limit: int = 100, offset: int = 0) -> List[dict]:
        """List all Thing Descriptions in directory.

        Args:
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of Thing Descriptions
        """
        if not self.session:
            await self.connect()

        # GET /things endpoint
        async with self.session.get(
            f"{self.directory_url}/things",
            params={'limit': limit, 'offset': offset}
        ) as response:
            if response.status == 200:
                results = await response.json()
                return results
            else:
                error = await response.text()
                raise Exception(f"List TDs failed ({response.status}): {error}")
```

#### Auto-Registration on Server Startup

**Update to:** `ot_simulator/opcua_simulator.py`

```python
async def start(self):
    """Start OPC UA server with optional TD Directory registration."""
    # Start OPC UA server
    await self.server.start()
    logger.info(f"OPC-UA server started at {self.config.endpoint}")

    # Auto-register with TD Directory if configured
    if self.config.td_directory.enabled:
        try:
            await self._register_with_td_directory()
        except Exception as e:
            logger.warning(f"TD Directory registration failed: {e}")
            logger.info("Server will continue without TD registration")

async def _register_with_td_directory(self):
    """Generate TD and register with directory."""
    # Generate Thing Description
    td_generator = ThingDescriptionGenerator(
        opcua_server=self,
        base_url=self.config.endpoint
    )

    td = await td_generator.generate_td(
        include_plc_nodes=self.config.td_directory.include_plc_nodes
    )

    # Add directory-specific metadata
    td['registration'] = {
        'registered': datetime.utcnow().isoformat() + 'Z',
        'ttl': self.config.td_directory.ttl_seconds
    }

    # Connect to TD Directory
    self.td_directory_client = ThingDescriptionDirectory(
        directory_url=self.config.td_directory.url,
        api_key=self.config.td_directory.api_key
    )

    await self.td_directory_client.connect()

    # Register TD
    registration_id = await self.td_directory_client.register_td(td)

    logger.info(f"Registered with TD Directory")
    logger.info(f"  Directory: {self.config.td_directory.url}")
    logger.info(f"  Registration ID: {registration_id}")

    # Start background task to refresh registration
    if self.config.td_directory.auto_refresh:
        self._td_refresh_task = asyncio.create_task(
            self._refresh_td_registration(td, registration_id)
        )

async def _refresh_td_registration(self, td: dict, registration_id: str):
    """Periodically refresh TD registration (keep-alive)."""
    refresh_interval = self.config.td_directory.refresh_interval_seconds

    while self._running:
        try:
            await asyncio.sleep(refresh_interval)

            # Update TD with latest timestamp
            td['modified'] = datetime.utcnow().isoformat() + 'Z'

            # Refresh registration
            await self.td_directory_client.update_td(registration_id, td)
            logger.debug(f"TD registration refreshed")

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"TD refresh failed: {e}")

async def stop(self):
    """Stop OPC UA server and unregister from TD Directory."""
    # Unregister from TD Directory
    if hasattr(self, 'td_directory_client') and self.td_directory_client:
        try:
            await self.td_directory_client.unregister_td()
            await self.td_directory_client.close()
            logger.info("Unregistered from TD Directory")
        except Exception as e:
            logger.warning(f"TD unregistration failed: {e}")

    # Stop server
    await self.server.stop()
    logger.info("OPC-UA server stopped")
```

#### Configuration Schema

**Update to:** `ot_simulator/config.yaml`

```yaml
opcua:
  # ... (existing config)

  # Thing Description Directory integration
  td_directory:
    enabled: true
    url: "http://localhost:8080"  # TD Directory server URL
    api_key: ""  # Optional API key
    ttl_seconds: 3600  # Time-to-live for registration
    auto_refresh: true  # Periodically refresh registration
    refresh_interval_seconds: 1800  # Refresh every 30 minutes
    include_plc_nodes: true  # Include PLC hierarchy in TD
```

---

### Phase 4: Semantic Enrichment (Week 6)

#### Ontology Definitions

**File:** `ot_simulator/opcua_ontology.py`

```python
"""Semantic ontology mappings for OPC UA nodes.

Supported ontologies:
- SAREF: Smart Applications REFerence ontology (https://saref.etsi.org/core/)
- SSN/SOSA: Semantic Sensor Network (https://www.w3.org/TR/vocab-ssn/)
- QUDT: Quantities, Units, Dimensions and Types (http://qudt.org/)
- Schema.org: General-purpose vocabulary (https://schema.org/)
"""

from typing import List, Dict, Any, Optional


# Sensor type to SAREF/SSN mapping
SENSOR_TYPE_ONTOLOGY: Dict[str, Dict[str, Any]] = {
    "temperature": {
        "@type": ["saref:TemperatureSensor", "sosa:Sensor", "opcua:AnalogItemType"],
        "saref:measuresProperty": "saref:Temperature",
        "sosa:observes": "saref:Temperature",
        "qudt:unit": "qudt:DegreeCelsius",
        "rdfs:comment": "Measures temperature in industrial environment"
    },
    "pressure": {
        "@type": ["saref:PressureSensor", "sosa:Sensor", "opcua:AnalogItemType"],
        "saref:measuresProperty": "saref:Pressure",
        "sosa:observes": "saref:Pressure",
        "qudt:unit": "qudt:Bar",
        "rdfs:comment": "Measures pressure in pipes, vessels, or systems"
    },
    "power": {
        "@type": ["saref:PowerSensor", "saref:EnergyMeter", "sosa:Sensor", "opcua:AnalogItemType"],
        "saref:measuresProperty": "saref:Power",
        "sosa:observes": "saref:Power",
        "qudt:unit": "qudt:Kilowatt",
        "rdfs:comment": "Measures electrical power consumption"
    },
    "vibration": {
        "@type": ["sosa:Sensor", "opcua:AnalogItemType"],
        "sosa:observes": "ex:Vibration",
        "qudt:unit": "qudt:MillimeterPerSecond",
        "rdfs:comment": "Measures mechanical vibration for predictive maintenance"
    },
    "flow": {
        "@type": ["saref:Sensor", "sosa:Sensor", "opcua:AnalogItemType"],
        "saref:measuresProperty": "ex:FlowRate",
        "sosa:observes": "ex:FlowRate",
        "qudt:unit": "qudt:CubicMeterPerHour",
        "rdfs:comment": "Measures fluid flow rate"
    },
    "level": {
        "@type": ["saref:LevelSensor", "sosa:Sensor", "opcua:AnalogItemType"],
        "saref:measuresProperty": "saref:Level",
        "sosa:observes": "saref:Level",
        "qudt:unit": "qudt:Meter",
        "rdfs:comment": "Measures liquid or solid material level in tanks"
    },
    "speed": {
        "@type": ["sosa:Sensor", "opcua:AnalogItemType"],
        "sosa:observes": "ex:RotationalSpeed",
        "qudt:unit": "qudt:RevolutionPerMinute",
        "rdfs:comment": "Measures rotational speed of motors or machinery"
    },
    "current": {
        "@type": ["saref:ElectricitySensor", "sosa:Sensor", "opcua:AnalogItemType"],
        "saref:measuresProperty": "saref:Current",
        "sosa:observes": "saref:Current",
        "qudt:unit": "qudt:Ampere",
        "rdfs:comment": "Measures electrical current"
    },
    "voltage": {
        "@type": ["saref:VoltageSensor", "sosa:Sensor", "opcua:AnalogItemType"],
        "saref:measuresProperty": "saref:Voltage",
        "sosa:observes": "saref:Voltage",
        "qudt:unit": "qudt:Volt",
        "rdfs:comment": "Measures electrical voltage"
    },
    "humidity": {
        "@type": ["saref:HumiditySensor", "sosa:Sensor", "opcua:AnalogItemType"],
        "saref:measuresProperty": "saref:Humidity",
        "sosa:observes": "saref:Humidity",
        "qudt:unit": "qudt:Percent",
        "rdfs:comment": "Measures relative humidity"
    },
}

# Industry to Schema.org/custom ontology mapping
INDUSTRY_ONTOLOGY: Dict[str, Dict[str, Any]] = {
    "mining": {
        "@type": ["schema:Place", "ex:MiningFacility"],
        "rdfs:label": "Mining Operations",
        "schema:industry": "https://www.naics.com/naics-code-description/?code=212",
        "ex:sectorCode": "212 - Mining (except Oil and Gas)",
        "rdfs:comment": "Ore extraction and mineral processing operations"
    },
    "utilities": {
        "@type": ["schema:Place", "ex:PowerGeneration"],
        "rdfs:label": "Utility Power Generation",
        "schema:industry": "https://www.naics.com/naics-code-description/?code=2211",
        "ex:sectorCode": "2211 - Electric Power Generation",
        "rdfs:comment": "Electricity generation and distribution"
    },
    "manufacturing": {
        "@type": ["schema:Factory", "ex:ManufacturingFacility"],
        "rdfs:label": "Manufacturing Operations",
        "schema:industry": "https://www.naics.com/naics-code-description/?code=31-33",
        "ex:sectorCode": "31-33 - Manufacturing",
        "rdfs:comment": "Production and assembly operations"
    },
    "oil_gas": {
        "@type": ["schema:Place", "ex:OilGasFacility"],
        "rdfs:label": "Oil & Gas Operations",
        "schema:industry": "https://www.naics.com/naics-code-description/?code=211",
        "ex:sectorCode": "211 - Oil and Gas Extraction",
        "rdfs:comment": "Petroleum and natural gas extraction"
    },
    "water_wastewater": {
        "@type": ["schema:WaterTreatment", "ex:WaterFacility"],
        "rdfs:label": "Water & Wastewater Treatment",
        "schema:industry": "https://www.naics.com/naics-code-description/?code=2213",
        "ex:sectorCode": "2213 - Water Supply and Irrigation Systems",
        "rdfs:comment": "Water treatment and distribution"
    },
    # Add all 16 industries...
}

# Equipment type ontology
EQUIPMENT_ONTOLOGY: Dict[str, Dict[str, Any]] = {
    "motor": {
        "@type": ["ex:ElectricMotor", "saref:Actuator"],
        "rdfs:label": "Electric Motor",
        "saref:hasFunction": "saref:ActuatorFunction",
        "ex:equipmentCategory": "Rotating Equipment"
    },
    "pump": {
        "@type": ["ex:Pump", "saref:Actuator"],
        "rdfs:label": "Centrifugal Pump",
        "saref:hasFunction": "ex:PumpingFunction",
        "ex:equipmentCategory": "Fluid Handling"
    },
    "crusher": {
        "@type": ["ex:Crusher", "ex:ProcessEquipment"],
        "rdfs:label": "Ore Crusher",
        "ex:equipmentCategory": "Material Processing"
    },
    # Add more equipment types...
}


def enrich_property_with_semantics(
    property_def: dict,
    sensor_type: str,
    industry: Optional[str] = None
) -> dict:
    """Add semantic annotations to property definition.

    Args:
        property_def: Base property definition
        sensor_type: Type of sensor (temperature, pressure, etc.)
        industry: Optional industry context

    Returns:
        Enriched property definition with ontology annotations
    """
    # Add sensor type semantics
    if sensor_type in SENSOR_TYPE_ONTOLOGY:
        ontology = SENSOR_TYPE_ONTOLOGY[sensor_type].copy()

        # Merge @type arrays
        if "@type" in property_def and "@type" in ontology:
            property_def["@type"] = list(set(property_def["@type"] + ontology["@type"]))
            del ontology["@type"]

        property_def.update(ontology)

    # Add industry context if provided
    if industry and industry in INDUSTRY_ONTOLOGY:
        property_def["ex:industry"] = INDUSTRY_ONTOLOGY[industry]

    return property_def


def create_observation(
    property_name: str,
    value: float,
    unit: str,
    timestamp: str,
    sensor_type: str
) -> dict:
    """Create SSN/SOSA Observation instance.

    Args:
        property_name: Property being observed
        value: Observed value
        unit: Unit of measurement
        timestamp: ISO 8601 timestamp
        sensor_type: Type of sensor

    Returns:
        SOSA Observation as dict
    """
    observation = {
        "@type": "sosa:Observation",
        "sosa:hasFeatureOfInterest": f"ex:{property_name}",
        "sosa:resultTime": timestamp,
        "sosa:hasResult": {
            "@type": "qudt:QuantityValue",
            "qudt:numericValue": value,
            "qudt:unit": unit
        }
    }

    # Add sensor reference
    if sensor_type in SENSOR_TYPE_ONTOLOGY:
        observation["sosa:madeBySensor"] = {
            "@type": SENSOR_TYPE_ONTOLOGY[sensor_type]["@type"]
        }

    return observation
```

#### Integration into Thing Description Generator

**Update to:** `ot_simulator/opcua_thing_description.py`

```python
from ot_simulator.opcua_ontology import (
    enrich_property_with_semantics,
    INDUSTRY_ONTOLOGY,
    EQUIPMENT_ONTOLOGY
)

async def _create_property_definition(self, node: Node) -> dict:
    """Create WoT Property from OPC UA Variable with semantic enrichment."""
    # ... (existing code to read node metadata)

    # Create base property definition
    property_def = {
        "title": display_name.Text,
        "description": description.Text if description else "",
        "type": "number",
        "observable": True,
        "forms": [...]  # existing forms
    }

    # Add optional metadata
    if unit:
        property_def["unit"] = unit
    if min_val is not None:
        property_def["minimum"] = min_val
    if max_val is not None:
        property_def["maximum"] = max_val

    # **ENRICH WITH SEMANTIC ANNOTATIONS**
    property_def = enrich_property_with_semantics(
        property_def=property_def,
        sensor_type=sensor_type,
        industry=self._extract_industry_from_path(browse_path)
    )

    return property_def

def _extract_industry_from_path(self, browse_path: str) -> Optional[str]:
    """Extract industry name from browse path.

    Example: "0:Root/0:Objects/2:Mining/2:crusher_1_power" -> "mining"
    """
    parts = browse_path.split('/')
    if len(parts) >= 3:
        industry_part = parts[2]  # "2:Mining"
        industry_name = industry_part.split(':')[1].lower()  # "mining"
        return industry_name
    return None
```

**Result Example:**

```json
{
  "properties": {
    "crusher_1_motor_power": {
      "@type": ["saref:PowerSensor", "saref:EnergyMeter", "sosa:Sensor", "opcua:AnalogItemType"],
      "title": "Crusher #1 Motor Power",
      "type": "number",
      "unit": "kW",
      "minimum": 0,
      "maximum": 500,
      "saref:measuresProperty": "saref:Power",
      "sosa:observes": "saref:Power",
      "qudt:unit": "qudt:Kilowatt",
      "ex:industry": {
        "@type": ["schema:Place", "ex:MiningFacility"],
        "rdfs:label": "Mining Operations",
        "schema:industry": "https://www.naics.com/naics-code-description/?code=212"
      },
      "forms": [...]
    }
  }
}
```

---

## Client-Side Implications

### Current OPC UA Client (`opcua2uc/protocols/opcua_client.py`)

#### What Works Today
✅ Connects to OPC UA servers (NoSecurity mode)
✅ Discovers variables via browsing
✅ Reads variable values
✅ Streams to Zero-Bus (protobuf format)
✅ Handles reconnection with exponential backoff

#### What Needs to Change for OPC UA 10101 Compliance

1. **Thing Description Consumption**
```python
# NEW: Initialize from Thing Description instead of endpoint
client = OPCUAWoTClient(td_url="http://server:8989/api/opcua/thing-description")
await client.connect()

# Read using WoT property names (semantic layer)
power = await client.read_property("crusher_1_motor_power")

# Subscribe using WoT observables
await client.observe_property("crusher_1_vibration", callback)
```

2. **Security Support**
```python
# Current: Anonymous only
client = Client(url=endpoint, timeout=10)

# NEW: Certificate-based authentication
client = Client(
    url=endpoint,
    certificate="client_cert.der",
    private_key="client_key.pem",
    security_policy="Basic256Sha256"
)

# NEW: Username/password authentication
client = Client(
    url=endpoint,
    username="operator",
    password="operator123",
    security_policy="Basic256Sha256"
)
```

3. **Semantic Awareness**
```python
# NEW: Filter by semantic types
temperature_sensors = client.get_properties_by_type("saref:TemperatureSensor")
power_sensors = client.get_properties_by_type("saref:PowerSensor")

# NEW: Query by industry
mining_sensors = client.get_properties_by_industry("mining")

# NEW: Ontology-based reasoning
critical_sensors = client.get_properties_by_criteria(
    semantic_type="saref:PowerSensor",
    industry="mining",
    max_value_gt=400  # Power > 400 kW
)
```

4. **TD Directory Discovery**
```python
# NEW: Discover servers via TD Directory
directory = ThingDescriptionDirectory("http://td-directory:8080")
tds = await directory.search_td(
    query="databricks ot simulator",
    type_filter=["saref:PowerSensor"]
)

# Connect to first result
if tds:
    client = OPCUAWoTClient(td=tds[0])
    await client.connect()
```

### Updated Client Architecture

```
┌─────────────────────────────────────────────┐
│         Zero-Bus Ingestion Layer            │
│  (opcua2uc/zerobus_ingest.py)              │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│       WoT Client Layer (NEW)                │
│  (opcua2uc/protocols/opcua_wot_client.py)  │
│  - Thing Description parsing                │
│  - Semantic property access                 │
│  - WoT affordance mapping                   │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│      OPC UA Protocol Client                 │
│  (opcua2uc/protocols/opcua_client.py)      │
│  - Native OPC UA connection                 │
│  - Certificate management                   │
│  - Browse/read/subscribe operations         │
└─────────────────────────────────────────────┘
```

---

## Benefits & Use Cases

### For Developers

**Before OPC UA 10101:**
```python
# 1. Get 50MB nodeset XML file
# 2. Install OPC UA SDK
# 3. Configure certificates
# 4. Write custom browse logic
client = opcua.Client("opc.tcp://server:4840")
await client.connect()
root = client.nodes.root
# Manually browse tree...
# Parse node structure...
# Map to application model...
```

**With OPC UA 10101:**
```python
# 1. Fetch lightweight JSON-LD Thing Description
td = await fetch("http://server:8989/api/opcua/thing-description")

# 2. Standard WoT client
client = WoTClient(td)
power = await client.read_property("crusher_1_motor_power")
# Done!
```

### For Data Scientists

**Semantic Queries:**
```python
# Find all temperature sensors across all industries
temp_sensors = client.get_properties_by_type("saref:TemperatureSensor")

# Get all sensors in mining industry
mining_data = client.get_properties_by_industry("mining")

# Reasoning: Find high-power motors
critical_motors = [
    prop for prop in client.properties
    if "saref:PowerSensor" in prop["@type"]
    and prop.get("maximum", 0) > 400
]
```

### For Integration Engineers

**Cross-Protocol Integration:**
```json
{
  "properties": {
    "crusher_power": {
      "forms": [
        {
          "href": "opc.tcp://server:4840?ns=2;s=mining/crusher_1_power",
          "subprotocol": "opcua"
        },
        {
          "href": "mqtt://broker:1883/mining/crusher_1/power",
          "subprotocol": "mqtt"
        },
        {
          "href": "modbus://gateway:502/40001",
          "subprotocol": "modbus"
        }
      ]
    }
  }
}
```

Client automatically selects best available protocol!

### For DevOps Engineers

**Service Discovery:**
```bash
# Discover all OT simulators
curl http://td-directory:8080/search?q=databricks

# Get specific simulator
curl http://td-directory:8080/things/{id}

# Health check via TD
curl http://server:8989/api/opcua/thing-description | jq '.title'
```

---

## References & Resources

### OPC UA 10101 Specification
- **Official Document**: https://reference.opcfoundation.org/WoT/Binding/v100/docs/
- **Release Date**: January 8, 2026
- **Version**: 1.00
- **Status**: Published

### W3C Web of Things
- **Thing Description 2.0**: https://w3c.github.io/wot-thing-description/
- **WoT Architecture**: https://www.w3.org/TR/wot-architecture/
- **WoT Discovery**: https://w3c.github.io/wot-discovery/
- **Protocol Bindings**: https://github.com/w3c/wot-binding-templates

### Semantic Ontologies
- **SAREF**: https://saref.etsi.org/core/
- **SSN/SOSA**: https://www.w3.org/TR/vocab-ssn/
- **QUDT**: http://qudt.org/schema/qudt/
- **Schema.org**: https://schema.org/

### Open Source Implementations
- **Eclipse Thingweb**: https://github.com/eclipse-thingweb/node-wot
  - Reference implementation of W3C WoT
  - OPC UA binding example
- **OPC Foundation UA-EdgeTranslator**: https://github.com/OPCFoundation/UA-EdgeTranslator
  - Thing Description examples
  - Protocol mapping patterns

### Standards Bodies
- **OPC Foundation**: https://opcfoundation.org/
- **W3C WoT Working Group**: https://www.w3.org/WoT/
- **ETSI SmartM2M**: https://www.etsi.org/technologies/smart-m2m

---

## Appendix A: Implementation Checklist

### Phase 1: Thing Description Generator
- [ ] Create `opcua_thing_description.py` module
- [ ] Implement node-to-property mapping
- [ ] Implement node-to-action mapping
- [ ] Add security definitions
- [ ] Create REST API endpoint `/api/opcua/thing-description`
- [ ] Add query parameter filtering
- [ ] Write unit tests
- [ ] Validate against W3C TD schema
- [ ] Update documentation

### Phase 2: Enhanced Security
- [ ] Create `opcua_certificates.py` module
- [ ] Implement certificate generation
- [ ] Implement certificate validation
- [ ] Add Basic256Sha256 security policy
- [ ] Add username/password authentication
- [ ] Update Thing Description security definitions
- [ ] Test secure connections
- [ ] Document certificate management
- [ ] Update configuration schema

### Phase 3: Thing Description Directory
- [ ] Create `opcua_td_directory.py` module
- [ ] Implement TD registration
- [ ] Implement TD update/refresh
- [ ] Implement TD unregistration
- [ ] Implement TD search
- [ ] Add auto-registration on server startup
- [ ] Add auto-unregistration on shutdown
- [ ] Add background refresh task
- [ ] Test directory integration
- [ ] Update configuration schema

### Phase 4: Semantic Enrichment
- [ ] Create `opcua_ontology.py` module
- [ ] Define sensor type ontology mappings
- [ ] Define industry ontology mappings
- [ ] Define equipment ontology mappings
- [ ] Integrate into TD generator
- [ ] Add SOSA observation support
- [ ] Test semantic queries
- [ ] Document ontology usage
- [ ] Provide mapping examples

### Phase 5: Client Enhancement
- [ ] Create `opcua_wot_client.py` module
- [ ] Implement TD loading/parsing
- [ ] Implement semantic property access
- [ ] Implement WoT affordance methods
- [ ] Add certificate-based auth
- [ ] Add username/password auth
- [ ] Test with TD-enabled servers
- [ ] Update Zero-Bus ingestion
- [ ] Write integration tests
- [ ] Update client documentation

---

## Appendix B: Testing Strategy

### Unit Tests
```python
# test_thing_description.py
async def test_generate_td():
    """Test Thing Description generation."""
    td_gen = ThingDescriptionGenerator(opcua_server, base_url)
    td = await td_gen.generate_td()

    assert '@context' in td
    assert 'title' in td
    assert 'properties' in td
    assert len(td['properties']) > 0

async def test_property_mapping():
    """Test OPC UA variable to WoT property mapping."""
    node = opcua_server.get_node("ns=2;s=mining/crusher_1_motor_power")
    property_def = await td_gen._create_property_definition(node)

    assert '@type' in property_def
    assert 'saref:PowerSensor' in property_def['@type']
    assert property_def['unit'] == 'kW'
    assert 'forms' in property_def
```

### Integration Tests
```python
# test_wot_integration.py
async def test_end_to_end_workflow():
    """Test complete WoT workflow."""
    # 1. Start server
    server = OPCUASimulator(config)
    await server.start()

    # 2. Generate TD
    td_url = "http://localhost:8989/api/opcua/thing-description"

    # 3. Connect client
    client = OPCUAWoTClient(td_url)
    await client.connect()

    # 4. Read property
    value = await client.read_property("crusher_1_motor_power")
    assert isinstance(value, float)

    # 5. Cleanup
    await client.disconnect()
    await server.stop()
```

### Validation Tests
```python
# test_td_validation.py
def test_td_schema_validation():
    """Validate TD against W3C schema."""
    td = load_td("examples/thing_description.json")

    # Validate using jsonschema
    schema = load_wot_td_schema()
    validate(td, schema)  # Raises if invalid
```

---

## Appendix C: Migration Guide

### Existing Deployments

**For Server Operators:**

1. **Add Thing Description endpoint** (no breaking changes)
```python
# Existing code continues to work
server = OPCUASimulator(config)
await server.start()

# NEW: TD endpoint automatically available
# GET http://localhost:8989/api/opcua/thing-description
```

2. **Enable security** (optional, but recommended)
```yaml
opcua:
  security_policy: "Basic256Sha256"  # Change from "NoSecurity"
  auth:
    enabled: true
    users:
      - username: "admin"
        password: "admin123"
```

3. **Register with TD Directory** (optional)
```yaml
opcua:
  td_directory:
    enabled: true
    url: "http://td-directory:8080"
```

**For Client Developers:**

1. **Continue using existing client** (no changes required)
```python
# Existing code works unchanged
client = OPCUAProtocolClient(endpoint="opc.tcp://server:4840")
await client.connect()
```

2. **Migrate to WoT client** (when ready)
```python
# NEW: Use Thing Description
client = OPCUAWoTClient("http://server:8989/api/opcua/thing-description")
await client.connect()
power = await client.read_property("crusher_1_motor_power")
```

3. **Benefits of migration:**
- Automatic endpoint discovery
- Semantic property access
- Cross-protocol compatibility
- Better security support

---

## Conclusion

OPC UA 10101 WoT Binding represents a significant step forward in industrial IoT interoperability. By implementing this specification, we can:

1. **Simplify Integration** - JSON-LD Thing Descriptions vs 50MB nodesets
2. **Enable Web-Native Access** - Standard HTTP/WebSocket alongside OPC UA
3. **Add Semantics** - Machine-readable ontologies for automated reasoning
4. **Improve Security** - Modern authentication (OAuth2, certificates)
5. **Enhance Discovery** - Thing Description Directories for service registry

Our implementation roadmap provides a phased approach:
- **Phase 1** (Weeks 1-2): Thing Description generation - Foundation
- **Phase 2** (Weeks 3-4): Enhanced security - Production readiness
- **Phase 3** (Week 5): TD Directory integration - Service discovery
- **Phase 4** (Week 6): Semantic enrichment - Advanced analytics

The current OPC UA implementation is solid. Adding WoT binding on top creates a powerful hybrid system that supports both traditional OPC UA clients AND modern web-native applications.

---

**Document Status**: ✅ Complete
**Next Steps**: Review, prioritize, and begin Phase 1 implementation
**Questions**: Contact the development team

