# Unity Catalog Table Schemas

This document describes the Unity Catalog table schemas for all three protocols (MQTT, Modbus, OPC-UA) used with the ZeroBus streaming connector.

## Overview

All tables use **Protocol Buffers (protobuf)** format for efficient binary serialization. The schemas are defined in `.proto` files and compiled to Python classes for use with the ZeroBus SDK.

**Key Design Decisions:**
- Timestamps are stored as `BIGINT` (microseconds since epoch) for precision and efficiency
- No JSON format - pure protobuf for maximum performance
- Schema validation is enforced by ZeroBus at stream creation time
- All tables use Delta format for ACID transactions and time travel

## Protobuf Schema Files

| Protocol | Proto File | Python Class |
|----------|-----------|--------------|
| MQTT | `ot_simulator/mqtt_bronze.proto` | `mqtt_bronze_pb2.MQTTBronzeRecord` |
| Modbus | `ot_simulator/modbus_bronze.proto` | `modbus_bronze_pb2.ModbusBronzeRecord` |
| OPC-UA | `ot_simulator/opcua_bronze.proto` | `opcua_bronze_pb2.OPCUABronzeRecord` |

## MQTT Schema

### Table: `mqtt.scada_data.mqtt_events_bronze`

**Purpose:** Bronze layer for MQTT sensor data streams from industrial IoT devices.

**Schema:**
```sql
CREATE TABLE mqtt.scada_data.mqtt_events_bronze (
    event_time BIGINT COMMENT 'Event timestamp in microseconds',
    ingest_time BIGINT COMMENT 'Ingestion timestamp in microseconds',
    source_name STRING COMMENT 'Name of the data source',
    topic STRING COMMENT 'MQTT topic',
    industry STRING COMMENT 'Industry category',
    sensor_name STRING COMMENT 'Sensor identifier',
    value DOUBLE COMMENT 'Numeric sensor value',
    value_string STRING COMMENT 'String sensor value',
    unit STRING COMMENT 'Unit of measurement',
    sensor_type STRING COMMENT 'Type of sensor',
    timestamp_ms BIGINT COMMENT 'Original MQTT timestamp in milliseconds',
    qos INT COMMENT 'MQTT Quality of Service level',
    retain BOOLEAN COMMENT 'MQTT retain flag',
    plc_name STRING COMMENT 'PLC system name',
    plc_vendor STRING COMMENT 'PLC vendor (Siemens, Rockwell, ABB, etc.)',
    plc_model STRING COMMENT 'PLC model (S7-1500, ControlLogix, etc.)'
)
USING DELTA
COMMENT 'Bronze layer for MQTT sensor data - protobuf format';
```

**Field Details:**

| Field | Type | Protobuf Type | Description |
|-------|------|---------------|-------------|
| `event_time` | BIGINT | int64 | Timestamp when event occurred (microseconds) |
| `ingest_time` | BIGINT | int64 | Timestamp when data was ingested (microseconds) |
| `source_name` | STRING | string | Identifier for the data source |
| `topic` | STRING | string | MQTT topic path (e.g., `scada/mining/temperature`) |
| `industry` | STRING | string | Industry vertical (mining, utilities, manufacturing, etc.) |
| `sensor_name` | STRING | string | Unique sensor identifier |
| `value` | DOUBLE | double | Numeric reading from sensor |
| `value_string` | STRING | string | String representation of value (for non-numeric data) |
| `unit` | STRING | string | Unit of measurement (°C, PSI, RPM, etc.) |
| `sensor_type` | STRING | string | Type of sensor (temperature, pressure, flow, etc.) |
| `timestamp_ms` | BIGINT | int64 | Original MQTT message timestamp (milliseconds) |
| `qos` | INT | int32 | MQTT Quality of Service level (0, 1, or 2) |
| `retain` | BOOLEAN | bool | MQTT retain flag |
| `plc_name` | STRING | string | PLC system name (if available) |
| `plc_vendor` | STRING | string | PLC vendor (Siemens, Rockwell, ABB, etc.) |
| `plc_model` | STRING | string | PLC model (S7-1500, ControlLogix, etc.) |

**Sample Query:**
```sql
SELECT
    DATE_FORMAT(FROM_UNIXTIME(event_time/1000000), 'yyyy-MM-dd HH:mm:ss') as event_timestamp,
    industry,
    sensor_name,
    value,
    unit,
    topic
FROM mqtt.scada_data.mqtt_events_bronze
WHERE industry = 'mining'
  AND event_time > (UNIX_TIMESTAMP() - 3600) * 1000000  -- Last hour
ORDER BY event_time DESC
LIMIT 100;
```

## Modbus Schema

### Table: `modbus.scada_data.modbus_events_bronze`

**Purpose:** Bronze layer for Modbus TCP/RTU sensor data from industrial control systems.

**Schema:**
```sql
CREATE TABLE modbus.scada_data.modbus_events_bronze (
    event_time BIGINT COMMENT 'Event timestamp in microseconds',
    ingest_time BIGINT COMMENT 'Ingestion timestamp in microseconds',
    source_name STRING COMMENT 'Name of the data source',
    slave_id INT COMMENT 'Modbus slave ID',
    register_address INT COMMENT 'Modbus register address',
    register_type STRING COMMENT 'Register type: holding, input, coil, discrete',
    industry STRING COMMENT 'Industry category',
    sensor_name STRING COMMENT 'Sensor identifier',
    sensor_path STRING COMMENT 'Full sensor path',
    sensor_type STRING COMMENT 'Type of sensor',
    unit STRING COMMENT 'Unit of measurement',
    raw_value DOUBLE COMMENT 'Raw sensor value',
    scaled_value INT COMMENT 'Scaled integer value',
    scale_factor INT COMMENT 'Scaling factor applied',
    plc_name STRING COMMENT 'PLC system name',
    plc_vendor STRING COMMENT 'PLC vendor (Siemens, Rockwell, ABB, etc.)',
    plc_model STRING COMMENT 'PLC model (S7-1500, ControlLogix, etc.)'
)
USING DELTA
COMMENT 'Bronze layer for Modbus sensor data - protobuf format';
```

**Field Details:**

| Field | Type | Protobuf Type | Description |
|-------|------|---------------|-------------|
| `event_time` | BIGINT | int64 | Timestamp when event occurred (microseconds) |
| `ingest_time` | BIGINT | int64 | Timestamp when data was ingested (microseconds) |
| `source_name` | STRING | string | Identifier for the Modbus source |
| `slave_id` | INT | int32 | Modbus slave/unit ID (1-247) |
| `register_address` | INT | int32 | Register address (0-65535) |
| `register_type` | STRING | string | Register type: holding, input, coil, discrete |
| `industry` | STRING | string | Industry vertical |
| `sensor_name` | STRING | string | Unique sensor identifier |
| `sensor_path` | STRING | string | Full hierarchical path to sensor |
| `sensor_type` | STRING | string | Type of sensor |
| `unit` | STRING | string | Unit of measurement |
| `raw_value` | DOUBLE | double | Raw unscaled value from register |
| `scaled_value` | INT | int32 | Scaled engineering unit value |
| `scale_factor` | INT | int32 | Scaling factor (divide raw by this) |

**Sample Query:**
```sql
SELECT
    DATE_FORMAT(FROM_UNIXTIME(event_time/1000000), 'yyyy-MM-dd HH:mm:ss') as event_timestamp,
    slave_id,
    register_address,
    register_type,
    sensor_name,
    raw_value / scale_factor as engineering_value,
    unit
FROM modbus.scada_data.modbus_events_bronze
WHERE register_type = 'holding'
  AND industry = 'oil_gas'
ORDER BY event_time DESC
LIMIT 100;
```

## OPC-UA Schema

### Table: `opcua.scada_data.opcua_events_bronze`

**Purpose:** Bronze layer for OPC-UA sensor data from SCADA systems and industrial automation.

**Schema:**
```sql
CREATE TABLE opcua.scada_data.opcua_events_bronze (
    event_time BIGINT COMMENT 'Event timestamp in microseconds',
    ingest_time BIGINT COMMENT 'Ingestion timestamp in microseconds',
    source_name STRING COMMENT 'Name of the data source',
    endpoint STRING COMMENT 'OPC-UA server endpoint URL',
    namespace INT COMMENT 'OPC-UA namespace index',
    node_id STRING COMMENT 'OPC-UA node identifier',
    browse_path STRING COMMENT 'OPC-UA browse path',
    status_code BIGINT COMMENT 'OPC-UA status code',
    status STRING COMMENT 'Status description',
    value_type STRING COMMENT 'Data type of the value',
    value STRING COMMENT 'String representation of value',
    value_num DOUBLE COMMENT 'Numeric value',
    raw BINARY COMMENT 'Raw binary data',
    plc_name STRING COMMENT 'PLC system name',
    plc_vendor STRING COMMENT 'PLC vendor (Siemens, Rockwell, ABB, etc.)',
    plc_model STRING COMMENT 'PLC model (S7-1500, ControlLogix, etc.)'
)
USING DELTA
COMMENT 'Bronze layer for OPC-UA sensor data - protobuf format';
```

**Field Details:**

| Field | Type | Protobuf Type | Description |
|-------|------|---------------|-------------|
| `event_time` | BIGINT | int64 | Timestamp when event occurred (microseconds) |
| `ingest_time` | BIGINT | int64 | Timestamp when data was ingested (microseconds) |
| `source_name` | STRING | string | Identifier for the OPC-UA source |
| `endpoint` | STRING | string | OPC-UA server endpoint URL |
| `namespace` | INT | int32 | OPC-UA namespace index |
| `node_id` | STRING | string | OPC-UA node identifier (e.g., `ns=2;s=Temperature`) |
| `browse_path` | STRING | string | Human-readable browse path |
| `status_code` | BIGINT | int64 | OPC-UA status code (0 = Good) |
| `status` | STRING | string | Status description (Good, Bad, Uncertain) |
| `value_type` | STRING | string | OPC-UA data type (Double, Int32, String, etc.) |
| `value` | STRING | string | String representation of any value type |
| `value_num` | DOUBLE | double | Numeric value (if applicable) |
| `raw` | BINARY | bytes | Raw binary data for complex types |

**Sample Query:**
```sql
SELECT
    DATE_FORMAT(FROM_UNIXTIME(event_time/1000000), 'yyyy-MM-dd HH:mm:ss') as event_timestamp,
    browse_path,
    value_type,
    CASE
        WHEN value_type IN ('Double', 'Float', 'Int32', 'UInt32') THEN value_num
        ELSE CAST(value AS DOUBLE)
    END as sensor_value,
    status
FROM opcua.scada_data.opcua_events_bronze
WHERE status = 'Good'
  AND namespace = 2
ORDER BY event_time DESC
LIMIT 100;
```

## Timestamp Conversion

All timestamps are stored as microseconds (µs) since Unix epoch. Use these formulas for conversion:

**To Human-Readable:**
```sql
-- Microseconds to timestamp
DATE_FORMAT(FROM_UNIXTIME(event_time/1000000), 'yyyy-MM-dd HH:mm:ss.SSS')

-- Microseconds to date
DATE(FROM_UNIXTIME(event_time/1000000))
```

**From Human-Readable:**
```sql
-- Current time in microseconds
UNIX_TIMESTAMP() * 1000000

-- Specific time in microseconds
UNIX_TIMESTAMP('2024-01-13 14:30:00') * 1000000

-- Last hour filter
WHERE event_time > (UNIX_TIMESTAMP() - 3600) * 1000000
```

## Schema Migration Notes

### Changes from JSON to Protobuf

The previous JSON-based schema had these differences:

**Removed Fields:**
- `host` - No longer tracked
- `port` - No longer tracked
- `protocol` - Implicit in table/catalog name

**Changed Field Types:**
- `event_time`: STRING → BIGINT (microseconds)
- `ingest_time`: STRING → BIGINT (microseconds)
- All numeric IDs: STRING → INT or BIGINT

**Benefits of Protobuf:**
- 5-10x smaller message size
- Faster serialization/deserialization
- Type safety and schema validation
- Better compression ratios
- Native Delta Lake integration

## Recreating Tables

If you need to recreate the tables (e.g., for schema changes), use this script:

```sql
-- Drop existing tables
DROP TABLE IF EXISTS modbus.scada_data.modbus_events_bronze;
DROP TABLE IF EXISTS mqtt.scada_data.mqtt_events_bronze;
DROP TABLE IF EXISTS opcua.scada_data.opcua_events_bronze;

-- Then run the CREATE TABLE statements above
```

## ZeroBus Configuration

Each protocol requires a ZeroBus configuration file in `ot_simulator/zerobus_configs/`:

- `mqtt_zerobus.json` - MQTT configuration
- `modbus_zerobus.json` - Modbus configuration
- `opcua_zerobus.json` - OPC-UA configuration

**Configuration Format:**
```json
{
  "workspace_host": "https://your-workspace.cloud.databricks.com",
  "zerobus_endpoint": "your-zerobus-endpoint.zerobus.region.cloud.databricks.com",
  "auth": {
    "client_id": "service-principal-client-id",
    "client_secret_encrypted": "encrypted-secret",
    "_encrypted": true
  },
  "target": {
    "catalog": "protocol_name",
    "schema": "scada_data",
    "table": "protocol_events_bronze"
  }
}
```

## Troubleshooting

### Schema Validation Errors

If you see errors like:
```
Proto field type mismatch for field "event_time": expected TYPE_STRING, actual TYPE_INT64
```

This means the Unity Catalog table schema doesn't match the protobuf schema. Solution:
1. Drop the table
2. Recreate with the correct schema from this document
3. Restart the simulator

### Descriptor Proto Errors

If you see:
```
ValueError: descriptor_proto is required in TableProperties when record_type is PROTO
```

This means the protobuf descriptor wasn't passed to ZeroBus. Check that:
1. Proto files are compiled: `./venv/bin/python -m grpc_tools.protoc ...`
2. `api_handlers.py` imports the `_pb2` modules
3. `get_protobuf_descriptor()` function exists and is called

## Performance Considerations

**Partitioning Strategy:**
```sql
-- Recommended partitioning by date for time-series data
ALTER TABLE mqtt.scada_data.mqtt_events_bronze
SET TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
);

-- Add partition column (optional)
ALTER TABLE mqtt.scada_data.mqtt_events_bronze
ADD COLUMN event_date DATE GENERATED ALWAYS AS (DATE(FROM_UNIXTIME(event_time/1000000)));
```

**Indexing:**
```sql
-- Create Z-ordering for common query patterns
OPTIMIZE mqtt.scada_data.mqtt_events_bronze
ZORDER BY (industry, sensor_name, event_time);
```

## Related Documentation

- [PROTOCOLS.md](PROTOCOLS.md) - Protocol-specific configuration guides
- [OPC_UA_CONNECTION_GUIDE.md](OPC_UA_CONNECTION_GUIDE.md) - OPC-UA setup instructions
- [README.md](README.md) - General project documentation

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2024-01-13 | 2.0 | Migrated to protobuf format, BIGINT timestamps |
| 2024-01-10 | 1.0 | Initial JSON-based schema |

---

**Last Updated:** 2024-01-13
**Maintainer:** OT Simulator Team
