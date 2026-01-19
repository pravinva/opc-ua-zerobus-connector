# Tag Normalization Implementation

## Overview

Tag normalization has been implemented to provide a unified, analytics-ready structure for industrial data from OPC-UA, Modbus, and MQTT protocols. This allows users without Ignition to benefit from normalized industrial data.

## Implementation Status

### ✅ Completed Components

#### 1. Core Normalization Classes
Located in: `iot_connector/connector/normalizer/`

- **tag_schema.py**: Defines `NormalizedTag` dataclass with unified schema
  - Fields: tag_id, tag_path, value, quality, timestamp, data_type, engineering_units
  - Context: site_id, line_id, equipment_id, signal_type
  - Metadata: Protocol-specific information
  - Methods: `to_dict()`, `from_dict()` for serialization

- **quality_mapper.py**: Maps protocol-specific quality to unified enum
  - OPC-UA: 32-bit status codes → GOOD/BAD/UNCERTAIN
  - Modbus: Transaction success → GOOD/BAD
  - MQTT: Retained/age heuristics → GOOD/UNCERTAIN

- **path_builder.py**: Generates hierarchical tag paths
  - Template-based path generation
  - Protocol-specific pattern extraction
  - Tag ID generation using SHA256 hash

#### 2. Protocol Normalizers
Located in: `iot_connector/connector/normalizer/`

- **base_normalizer.py**: Abstract base class
  - Common timestamp extraction
  - Data type inference
  - Metadata building
  - Context extraction

- **opcua_normalizer.py**: OPC-UA specific
  - Browse path parsing
  - Status code mapping
  - Engineering units extraction
  - Source/server timestamp handling

- **modbus_normalizer.py**: Modbus specific
  - Register transformation (int16, int32, uint32, float32)
  - Byte/word order handling
  - Scale factor application
  - Exception code mapping

- **mqtt_normalizer.py**: MQTT specific
  - JSON payload parsing
  - Topic hierarchy extraction
  - Message age calculation
  - Retained message handling

#### 3. Configuration Files
Located in: `iot_connector/config/`

- **normalization_config.yaml**: Main configuration
  - Mode: raw | normalized
  - Path templates per protocol
  - Quality thresholds
  - Output tables
  - Feature flags

- **tag_templates.yaml**: Path templates reference
  - ISA-95 hierarchy
  - Purdue Model
  - Asset-based
  - Location-based
  - Signal mappings

#### 4. Management Layer

- **normalization_manager.py**: Centralized manager
  - Configuration loading
  - Normalizer instantiation
  - Enable/disable control
  - Output table routing

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Protocol Clients                          │
│  (OPCUAClient, ModbusClient, MQTTClient)                    │
└──────────────────────┬──────────────────────────────────────┘
                       │ Raw Data
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Normalization Manager                           │
│  - Check if normalization enabled                           │
│  - Route to appropriate normalizer                          │
│  - Handle dual-write mode                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┴──────────────┐
         │                             │
         ▼                             ▼
   ┌──────────┐               ┌──────────────┐
   │   Raw    │               │  Normalized  │
   │   Mode   │               │     Mode     │
   └────┬─────┘               └──────┬───────┘
        │                             │
        ▼                             ▼
 ProtocolRecord              ┌────────────────┐
 (existing format)           │  Normalizers   │
                             ├────────────────┤
                             │ OPCUANormalizer│
                             │ ModbusNormalizer
                             │ MQTTNormalizer │
                             └────────┬───────┘
                                      │
                                      ▼
                             ┌────────────────┐
                             │ NormalizedTag  │
                             │ (unified schema)
                             └────────┬───────┘
                                      │
        ┌─────────────────────────────┴─────────────────┐
        │                                                │
        ▼                                                ▼
  raw_table                                     normalized_table
  (optional)                                    main.iot_bronze.normalized_tags
```

---

## Unified Schema

All protocols produce the same schema when normalized:

```python
{
    "tag_id": "a1b2c3d4e5f67890",
    "tag_path": "columbus/line3/press1/hydraulic_pressure",
    "value": 75.3,
    "quality": "good",
    "timestamp": "2025-01-19T10:30:45.123Z",
    "data_type": "float",
    "engineering_units": "bar",
    "source_protocol": "modbus",
    "source_identifier": "192.168.1.100:40001",
    "source_address": "192.168.1.100",
    "site_id": "columbus",
    "line_id": "line3",
    "equipment_id": "press1",
    "signal_type": "hydraulic_pressure",
    "metadata": {
        "modbus_register_address": 40001,
        "modbus_device_address": "192.168.1.100",
        "modbus_function_code": 3
    }
}
```

---

## Usage Examples

### Enable Normalization via Config

Edit `iot_connector/config/normalization_config.yaml`:

```yaml
# Change mode from 'raw' to 'normalized'
mode: normalized

# Or use feature flag
features:
  normalization_enabled: true
```

### Enable Normalization via Code

```python
from connector.normalizer import get_normalization_manager

# Get manager
manager = get_normalization_manager()

# Enable normalization
manager.set_enabled(True)

# Get normalizer for a protocol
opcua_normalizer = manager.get_normalizer("opcua")
```

### Normalize Data

```python
from connector.normalizer import OPCUANormalizer

# Create normalizer
normalizer = OPCUANormalizer(config)

# Raw OPC-UA data
raw_data = {
    "node_id": "ns=2;s=Line3.Machine1.Temperature",
    "value": {
        "value": 75.3,
        "source_timestamp": "2025-01-19T10:30:45.123Z",
        "status_code": 0
    },
    "browse_path": "Objects/Columbus/Line3/Machine1/Temperature",
    "engineering_units": "celsius",
    "server_url": "opc.tcp://plc1:4840"
}

# Normalize
normalized = normalizer.normalize(raw_data)

# Convert to dict for sending to ZeroBus
data_dict = normalized.to_dict()
```

---

## Integration Steps

### Step 1: Update Protocol Clients

Each protocol client needs to be updated to use normalization. Here's the pattern:

```python
class OPCUAClient(ProtocolClient):
    def __init__(self, ...):
        # ... existing code ...

        # Add normalization manager
        from connector.normalizer import get_normalization_manager
        self.norm_manager = get_normalization_manager()

    def _process_data(self, raw_data):
        # Check if normalization is enabled
        if self.norm_manager.is_enabled():
            # Get normalizer
            normalizer = self.norm_manager.get_normalizer("opcua")

            if normalizer:
                try:
                    # Normalize data
                    normalized = normalizer.normalize(raw_data)

                    # Send normalized data
                    self.on_record(normalized.to_dict())

                    # Optionally write raw too
                    if self.norm_manager.should_write_both():
                        self.on_record(raw_data)  # Send to raw table

                    return
                except Exception as e:
                    logger.error(f"Normalization failed: {e}")
                    # Fall through to raw mode

        # Raw mode (existing behavior)
        self.on_record(raw_data)
```

### Step 2: Update Web GUI

Add checkbox to Web GUI for enabling/disabling normalization:

**Location**: `iot_connector/connector/web_gui.py`

Add to settings or configuration section:

```html
<div class="form-group">
    <label>
        <input type="checkbox" id="normalization-enabled"
               onchange="toggleNormalization(this.checked)">
        Enable Tag Normalization
    </label>
    <small>Convert raw protocol data to unified tag structure</small>
</div>

<script>
async function toggleNormalization(enabled) {
    try {
        const response = await fetch('/api/normalization/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled })
        });

        const result = await response.json();

        if (result.success) {
            alert(`Normalization ${enabled ? 'enabled' : 'disabled'}`);
        } else {
            alert(`Failed: ${result.error}`);
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}
</script>
```

Add API endpoint:

```python
async def handle_toggle_normalization(self, request):
    """Toggle normalization on/off."""
    data = await request.json()
    enabled = data.get('enabled', False)

    from connector.normalizer import get_normalization_manager
    manager = get_normalization_manager()
    manager.set_enabled(enabled)

    return web.json_response({
        'success': True,
        'enabled': enabled
    })
```

### Step 3: Update ZeroBus Configuration

Configure ZeroBus to write to the normalized table when normalization is enabled:

```python
# In bridge.py or wherever ZeroBus writes occur

from connector.normalizer import get_normalization_manager

manager = get_normalization_manager()

if manager.is_enabled():
    table = manager.get_output_table(normalized=True)
else:
    table = manager.get_output_table(normalized=False)

# Write to appropriate table
zerobus_client.write(table, data)
```

---

## Testing

### Unit Tests

Create tests in `iot_connector/tests/`:

```python
# test_normalizer.py
from connector.normalizer import OPCUANormalizer, TagQuality

def test_opcua_normalizer():
    normalizer = OPCUANormalizer({})

    raw_data = {
        "node_id": "ns=2;s=Line3.Temp",
        "value": {"value": 75.3, "status_code": 0},
        "server_url": "opc.tcp://localhost:4840"
    }

    normalized = normalizer.normalize(raw_data)

    assert normalized.value == 75.3
    assert normalized.quality == TagQuality.GOOD
    assert normalized.source_protocol == "opcua"
```

### Integration Test

Test end-to-end flow:

```bash
# 1. Enable normalization
cd iot_connector
python -c "
from connector.normalizer import get_normalization_manager
manager = get_normalization_manager('config/normalization_config.yaml')
manager.set_enabled(True)
print(f'Normalization enabled: {manager.is_enabled()}')
"

# 2. Start connector
python -m connector

# 3. Send test data through OPC-UA/MQTT/Modbus
# 4. Verify normalized data in Delta table
```

---

## Delta Table Schema

Create the normalized table in Databricks:

```sql
CREATE TABLE IF NOT EXISTS main.iot_bronze.normalized_tags (
    tag_id STRING COMMENT 'Unique tag identifier (hash)',
    tag_path STRING COMMENT 'Hierarchical tag path',
    value VARIANT COMMENT 'Tag value (any type)',
    quality STRING COMMENT 'Quality code: good, bad, uncertain',
    timestamp TIMESTAMP COMMENT 'Event timestamp (UTC)',
    data_type STRING COMMENT 'Data type: float, int, bool, string, timestamp',
    engineering_units STRING COMMENT 'Engineering units (e.g., celsius, bar)',
    source_protocol STRING COMMENT 'Source protocol: opcua, modbus, mqtt',
    source_identifier STRING COMMENT 'Protocol-specific identifier',
    source_address STRING COMMENT 'Device/server address',
    site_id STRING COMMENT 'Site identifier',
    line_id STRING COMMENT 'Production line identifier',
    equipment_id STRING COMMENT 'Equipment identifier',
    signal_type STRING COMMENT 'Signal type',
    metadata MAP<STRING, STRING> COMMENT 'Protocol-specific metadata'
)
PARTITIONED BY (DATE(timestamp), site_id)
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);
```

---

## Configuration Reference

### normalization_config.yaml Fields

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `mode` | string | Operating mode: "raw" or "normalized" | "raw" |
| `path_building.default_template` | string | Default path template | "{site_id}/{line_id}/{equipment_id}/{signal_type}" |
| `path_building.opcua_template` | string | OPC-UA specific template | (uses default) |
| `quality.mqtt_age_threshold` | float | MQTT age threshold (seconds) | 300 |
| `output.normalized_table` | string | Target Delta table for normalized data | "main.iot_bronze.normalized_tags" |
| `output.raw_table` | string | Target Delta table for raw data | "main.iot_bronze.raw_protocol_data" |
| `output.write_both` | bool | Write both raw and normalized | false |
| `features.normalization_enabled` | bool | Enable normalization | false |

---

## Next Steps

### Immediate (Required for Full Functionality)

1. **Integrate with Protocol Clients** ✋ IN PROGRESS
   - Update MQTT client
   - Update OPC-UA client
   - Update Modbus client

2. **Add Web UI Checkbox** ⏳ PENDING
   - Add toggle in GUI
   - Add API endpoint
   - Test enable/disable

3. **Update ZeroBus Writer** ⏳ PENDING
   - Route to correct table based on mode
   - Handle dual-write mode

### Testing (Before Production)

4. **Unit Tests** ⏳ PENDING
   - Test each normalizer
   - Test quality mapper
   - Test path builder

5. **Integration Tests** ⏳ PENDING
   - End-to-end flow test
   - Multi-protocol test
   - Dual-write test

### Future Enhancements

6. **Advanced Features**
   - Tag metadata enrichment
   - Custom path templates per source
   - Real-time normalization statistics
   - Normalization error dashboard

---

## Troubleshooting

### Normalization Not Working

1. Check if enabled:
```python
from connector.normalizer import get_normalization_manager
manager = get_normalization_manager()
print(f"Enabled: {manager.is_enabled()}")
```

2. Check config file:
```bash
cat iot_connector/config/normalization_config.yaml | grep "mode:"
```

3. Check logs:
```bash
docker logs databricks-iot-connector | grep -i "normalization"
```

### Quality Mapping Issues

Check protocol-specific quality data is provided:

- **OPC-UA**: Ensure `status_code` in value dict
- **Modbus**: Ensure `success`, `exception_code`, `timeout` fields
- **MQTT**: Ensure `retained`, `timestamp` fields

### Path Building Issues

Verify context is provided:

```python
# Add context to raw_data
raw_data["config"] = {
    "site_id": "columbus",
    "line_id": "line3",
    "equipment_id": "press1"
}
```

---

## Contact & Support

For issues or questions:
- Check logs: `docker logs databricks-iot-connector`
- Review config: `iot_connector/config/normalization_config.yaml`
- Test normalizers: Run unit tests in `iot_connector/tests/`

---

**Implementation Date**: 2025-01-19
**Version**: 1.0
**Status**: Core components complete, integration pending
