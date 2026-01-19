# ZeroBus Integration with Normalized Tags

## Overview

This guide shows how to enable ZeroBus to write **normalized tags** from OPC-UA, MQTT, and Modbus protocols to Databricks Unity Catalog tables.

## Architecture Flow

```
┌──────────────────────────────────────────────────────────────┐
│           Protocol Clients (OPC-UA, MQTT, Modbus)            │
│                                                                │
│  • OPCUAClient reads node data                               │
│  • MQTTClient subscribes to topics                           │
│  • ModbusClient polls registers                             │
└──────────────────────┬───────────────────────────────────────┘
                       │ Raw Protocol Data
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                  Tag Normalization Layer                      │
│                                                                │
│  IF normalization_enabled:                                   │
│    • Transform to unified schema                             │
│    • Map quality codes (good/bad/uncertain)                  │
│    • Build hierarchical tag paths                            │
│    • Extract context (site/line/equipment)                   │
│  ELSE:                                                        │
│    • Pass through raw ProtocolRecord                         │
└──────────────────────┬───────────────────────────────────────┘
                       │ Normalized Tag OR Raw Record
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                    Unified Bridge                             │
│                                                                │
│  • Receives records via on_record() callback                 │
│  • Routes to backpressure manager                            │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                 Backpressure Manager                          │
│                                                                │
│  • In-memory queue (10,000 records)                          │
│  • Disk spool (when memory full)                             │
│  • Dead letter queue (for invalid records)                   │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                    Batch Processor                            │
│                                                                │
│  • Batches records (100 records or 5 seconds)                │
│  • Converts to Protobuf format                               │
│  • Applies compression                                       │
└──────────────────────┬───────────────────────────────────────┘
                       │ Protobuf Batches
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                    ZeroBus Client                             │
│                                                                │
│  • OAuth2 authentication                                     │
│  • HTTP/2 connection to Databricks                           │
│  • Retry with exponential backoff                            │
│  • Circuit breaker protection                                │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTPS
                       ▼
┌──────────────────────────────────────────────────────────────┐
│               Databricks Unity Catalog                        │
│                                                                │
│  • catalog: iot_data                                         │
│  • schema: bronze                                            │
│  • table: normalized_tags (or raw_protocol_data)            │
└──────────────────────────────────────────────────────────────┘
```

## Step 1: Enable Tag Normalization

### Option A: Via Web UI (Recommended)

1. Open the connector Web UI at `http://localhost:8080`
2. Navigate to **Advanced Settings** section
3. Check "**Enable Tag Normalization**" checkbox
4. Click "**Save Settings**"
5. Restart the connector

### Option B: Via Config File

Edit `iot_connector/config/normalization_config.yaml`:

```yaml
# Enable normalized mode
mode: normalized  # Change from 'raw' to 'normalized'

features:
  normalization_enabled: true  # Set to true

# Output tables
output:
  normalized_table: "main.iot_bronze.normalized_tags"
  raw_table: "main.iot_bronze.raw_protocol_data"
  write_both: false  # Set to true to write both raw and normalized
```

### Option C: Via Python Code

```python
from connector.normalizer import get_normalization_manager

manager = get_normalization_manager()
manager.set_enabled(True)
```

## Step 2: Configure ZeroBus Connection

Edit `iot_connector/config/connector.yaml`:

### 2.1 Enable ZeroBus

```yaml
zerobus:
  enabled: true  # Set to true to enable ZeroBus

  # Databricks workspace and ZeroBus endpoint
  workspace_host: "https://your-workspace.cloud.databricks.com"
  zerobus_endpoint: "your-endpoint.zerobus.region.cloud.databricks.com"
```

### 2.2 Configure Authentication

**Using OAuth2 Service Principal (Recommended)**:

```yaml
zerobus:
  auth:
    client_id: "${DATABRICKS_CLIENT_ID}"
    client_secret: "${DATABRICKS_CLIENT_SECRET}"
    token_endpoint: "https://your-workspace.cloud.databricks.com/oidc/v1/token"
```

Set environment variables:
```bash
export DATABRICKS_CLIENT_ID="your-client-id"
export DATABRICKS_CLIENT_SECRET="your-client-secret"
```

**Using Personal Access Token** (For Development):

```yaml
zerobus:
  auth:
    access_token: "${DATABRICKS_TOKEN}"
```

Set environment variable:
```bash
export DATABRICKS_TOKEN="dapi..."
```

### 2.3 Configure Target Table

**For Normalized Tags**:

```yaml
zerobus:
  target:
    catalog: "main"
    schema: "iot_bronze"
    table: "normalized_tags"  # Target table for normalized data
```

**For Raw Protocol Data**:

```yaml
zerobus:
  target:
    catalog: "main"
    schema: "iot_bronze"
    table: "raw_protocol_data"  # Target table for raw data
```

### 2.4 Configure Connection Settings

```yaml
zerobus:
  connection:
    timeout_seconds: 30
    max_retries: 3
    retry_backoff_multiplier: 2
    health_check_interval_seconds: 60

  # Batching settings
  batch:
    max_records: 1000  # Records per batch
    timeout_seconds: 5.0  # Max wait time before sending partial batch
```

## Step 3: Configure Protocol Sources

### 3.1 OPC-UA Source with Normalization

```yaml
sources:
  - name: "plant_floor_opcua"
    protocol: "opcua"
    enabled: true
    endpoint: "opc.tcp://localhost:4840"

    # Context for tag normalization
    site_id: "columbus"
    line_id: "line3"
    equipment_id: "plc1"

    # Enable normalization for this source
    normalization_enabled: true

    # OPC-UA specific settings
    variable_limit: 25
    publishing_interval_ms: 1000
```

### 3.2 MQTT Source with Normalization

```yaml
sources:
  - name: "sensor_network_mqtt"
    protocol: "mqtt"
    enabled: true
    endpoint: "mqtt://localhost:1883"

    # Context for tag normalization
    site_id: "columbus"
    line_id: "line3"
    equipment_id: "press1"

    # Enable normalization
    normalization_enabled: true

    # MQTT specific settings
    topics: ["columbus/+/+/#"]
    qos: 1
    payload_format: "json"
```

### 3.3 Modbus Source with Normalization

```yaml
sources:
  - name: "plc_modbus_tcp"
    protocol: "modbus"
    enabled: true
    endpoint: "modbus://localhost:5020"

    # Context for tag normalization
    site_id: "columbus"
    line_id: "line3"
    equipment_id: "conveyor1"

    # Enable normalization
    normalization_enabled: true

    # Modbus specific settings
    unit_id: 1
    poll_interval_ms: 1000

    registers:
      - type: "holding"
        address: 0
        count: 10
        name: "motor_speed"
        scale: 1.0
        offset: 0.0
        units: "rpm"
```

## Step 4: Create Databricks Tables

### 4.1 Normalized Tags Table (Recommended)

```sql
CREATE TABLE IF NOT EXISTS main.iot_bronze.normalized_tags (
    -- Unified Tag Schema
    tag_id STRING COMMENT 'Unique tag identifier (SHA256 hash)',
    tag_path STRING COMMENT 'Hierarchical tag path: site/line/equipment/signal',
    value VARIANT COMMENT 'Tag value (any type)',
    quality STRING COMMENT 'Unified quality: good, bad, uncertain',
    timestamp TIMESTAMP COMMENT 'Event timestamp (UTC)',
    data_type STRING COMMENT 'Data type: float, int, bool, string, timestamp',
    engineering_units STRING COMMENT 'Engineering units (e.g., rpm, bar, celsius)',

    -- Source Information
    source_protocol STRING COMMENT 'Source protocol: opcua, mqtt, modbus',
    source_identifier STRING COMMENT 'Protocol-specific identifier',
    source_address STRING COMMENT 'Device/server address',

    -- Context (ISA-95 Hierarchy)
    site_id STRING COMMENT 'Site identifier',
    line_id STRING COMMENT 'Production line identifier',
    equipment_id STRING COMMENT 'Equipment identifier',
    signal_type STRING COMMENT 'Signal type (e.g., temperature, pressure)',

    -- Protocol-Specific Metadata
    metadata MAP<STRING, STRING> COMMENT 'Protocol-specific metadata'
)
USING DELTA
PARTITIONED BY (DATE(timestamp), site_id)
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true',
    'delta.minReaderVersion' = '3',
    'delta.minWriterVersion' = '7'
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tag_path ON main.iot_bronze.normalized_tags (tag_path);
CREATE INDEX IF NOT EXISTS idx_equipment ON main.iot_bronze.normalized_tags (equipment_id);
```

### 4.2 Raw Protocol Data Table (Optional)

```sql
CREATE TABLE IF NOT EXISTS main.iot_bronze.raw_protocol_data (
    -- Event Information
    event_time_ms BIGINT COMMENT 'Event timestamp in milliseconds',
    source_name STRING COMMENT 'Source name from config',
    endpoint STRING COMMENT 'Protocol endpoint',
    protocol_type STRING COMMENT 'Protocol type: OPCUA, MQTT, MODBUS',

    -- Data
    topic_or_path STRING COMMENT 'MQTT topic or OPC-UA node path',
    value VARIANT COMMENT 'Raw value',
    value_type STRING COMMENT 'Value type',
    value_num DOUBLE COMMENT 'Numeric value (if applicable)',

    -- Status
    status_code INT COMMENT 'Protocol-specific status code',
    status STRING COMMENT 'Status message',

    -- Metadata
    metadata MAP<STRING, STRING> COMMENT 'Protocol-specific metadata'
)
USING DELTA
PARTITIONED BY (DATE(FROM_UNIXTIME(event_time_ms / 1000)), protocol_type)
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);
```

## Step 5: Start the Connector

### Using Docker

```bash
# Set environment variables
export DATABRICKS_CLIENT_ID="your-client-id"
export DATABRICKS_CLIENT_SECRET="your-client-secret"

# Start connector
docker-compose -f docker-compose.connector.yml up -d

# Check logs
docker logs -f iot-connector
```

### Using Python Directly

```bash
cd iot_connector

# Set environment variables
export DATABRICKS_CLIENT_ID="your-client-id"
export DATABRICKS_CLIENT_SECRET="your-client-secret"

# Start connector
python -m connector --config config/connector.yaml
```

## Step 6: Verify Data Flow

### 6.1 Check Connector Logs

```bash
docker logs iot-connector | grep -E "normalization|ZeroBus|batch"
```

Expected output:
```
2026-01-19 03:46:35 - INFO - Tag normalization enabled
2026-01-19 03:46:35 - INFO - ZeroBus enabled - connecting to Databricks...
2026-01-19 03:46:36 - INFO - ✓ Connected to ZeroBus
2026-01-19 03:46:37 - INFO - OPC-UA normalizer initialized
2026-01-19 03:46:37 - INFO - MQTT normalizer initialized
2026-01-19 03:46:37 - INFO - Modbus normalizer initialized
2026-01-19 03:46:40 - INFO - Batch sent: 100 records, 45.2 KB
```

### 6.2 Query Normalized Tags in Databricks

```sql
-- Check recent normalized tags
SELECT
    tag_id,
    tag_path,
    value,
    quality,
    timestamp,
    source_protocol,
    site_id,
    equipment_id
FROM main.iot_bronze.normalized_tags
WHERE timestamp > CURRENT_TIMESTAMP() - INTERVAL 5 MINUTES
ORDER BY timestamp DESC
LIMIT 100;
```

Expected results:
```
+------------------+---------------------------------------------+-------+--------+-------------------+----------------+-----------+--------------+
| tag_id           | tag_path                                    | value | quality| timestamp         | source_protocol| site_id   | equipment_id |
+------------------+---------------------------------------------+-------+--------+-------------------+----------------+-----------+--------------+
| 51d3f08d58c91570 | columbus/line3/plc1/temperature            | 75.3  | good   | 2026-01-19 03:46..| opcua          | columbus  | plc1         |
| f5b687a075c6296f | columbus/line3/press1/hydraulic_pressure   | 85.2  | good   | 2026-01-19 03:46..| mqtt           | columbus  | press1       |
| 70bc24fcf498d569 | columbus/line3/conveyor1/motor_speed       | 1500.0| good   | 2026-01-19 03:46..| modbus         | columbus  | conveyor1    |
+------------------+---------------------------------------------+-------+--------+-------------------+----------------+-----------+--------------+
```

### 6.3 Query by Protocol

```sql
-- OPC-UA tags only
SELECT tag_path, value, quality, timestamp
FROM main.iot_bronze.normalized_tags
WHERE source_protocol = 'opcua'
  AND timestamp > CURRENT_TIMESTAMP() - INTERVAL 1 HOUR
ORDER BY timestamp DESC;

-- MQTT tags only
SELECT tag_path, value, quality, timestamp
FROM main.iot_bronze.normalized_tags
WHERE source_protocol = 'mqtt'
  AND timestamp > CURRENT_TIMESTAMP() - INTERVAL 1 HOUR
ORDER BY timestamp DESC;

-- Modbus tags only
SELECT tag_path, value, quality, timestamp
FROM main.iot_bronze.normalized_tags
WHERE source_protocol = 'modbus'
  AND timestamp > CURRENT_TIMESTAMP() - INTERVAL 1 HOUR
ORDER BY timestamp DESC;
```

### 6.4 Query by Equipment

```sql
-- All tags from specific equipment
SELECT
    tag_path,
    value,
    quality,
    timestamp,
    source_protocol
FROM main.iot_bronze.normalized_tags
WHERE equipment_id = 'plc1'
  AND timestamp > CURRENT_TIMESTAMP() - INTERVAL 1 HOUR
ORDER BY timestamp DESC;
```

### 6.5 Cross-Protocol Analytics

```sql
-- Compare tags across protocols
SELECT
    source_protocol,
    COUNT(*) as tag_count,
    COUNT(DISTINCT equipment_id) as equipment_count,
    AVG(CAST(value AS DOUBLE)) as avg_value
FROM main.iot_bronze.normalized_tags
WHERE timestamp > CURRENT_TIMESTAMP() - INTERVAL 1 HOUR
  AND data_type = 'float'
GROUP BY source_protocol
ORDER BY source_protocol;
```

## Step 7: Monitor Performance

### 7.1 Check Backpressure Queue

```bash
curl http://localhost:8080/api/stats
```

Expected response:
```json
{
  "queue_depth": 42,
  "queue_max_size": 10000,
  "queue_utilization": 0.0042,
  "records_enqueued": 15234,
  "records_dropped": 0,
  "batches_sent": 152
}
```

### 7.2 Check ZeroBus Metrics

```sql
-- Records written per minute
SELECT
    DATE_TRUNC('minute', timestamp) as minute,
    COUNT(*) as records_per_minute
FROM main.iot_bronze.normalized_tags
WHERE timestamp > CURRENT_TIMESTAMP() - INTERVAL 1 HOUR
GROUP BY DATE_TRUNC('minute', timestamp)
ORDER BY minute DESC;
```

### 7.3 Prometheus Metrics (Optional)

If Prometheus is enabled:

```bash
curl http://localhost:9090/metrics | grep iot_connector
```

Expected metrics:
```
iot_connector_records_received_total 15234
iot_connector_records_enqueued_total 15234
iot_connector_records_dropped_total 0
iot_connector_batches_sent_total 152
iot_connector_zerobus_connection_status 1
```

## Dual-Write Mode (Write Both Raw and Normalized)

If you want to write **both** raw and normalized data:

### 1. Enable in Normalization Config

```yaml
# iot_connector/config/normalization_config.yaml
output:
  write_both: true  # Write both raw and normalized
  normalized_table: "main.iot_bronze.normalized_tags"
  raw_table: "main.iot_bronze.raw_protocol_data"
```

### 2. Update Bridge Logic

The bridge will need to be updated to handle dual-write:

```python
# In bridge.py _on_record method
def _on_record(self, record: Dict[str, Any]):
    """Handle incoming record from protocol client."""

    # Check if this is a normalized tag
    is_normalized = 'tag_id' in record and 'tag_path' in record

    # Get normalization manager
    from connector.normalizer import get_normalization_manager
    manager = get_normalization_manager()

    if is_normalized and manager.should_write_both():
        # Write normalized to normalized_table
        self.backpressure.enqueue(record, table="normalized_tags")

        # Also write raw (convert back to ProtocolRecord format)
        raw_record = self._convert_to_raw(record)
        self.backpressure.enqueue(raw_record, table="raw_protocol_data")
    else:
        # Write to appropriate table
        table = "normalized_tags" if is_normalized else "raw_protocol_data"
        self.backpressure.enqueue(record, table=table)
```

## Troubleshooting

### Issue: No Data in Databricks

**Check 1**: Verify ZeroBus is enabled
```bash
grep "zerobus:" iot_connector/config/connector.yaml
```

**Check 2**: Verify authentication
```bash
echo $DATABRICKS_CLIENT_ID
echo $DATABRICKS_CLIENT_SECRET
```

**Check 3**: Check connector logs
```bash
docker logs iot-connector | grep -i "error\|fail"
```

### Issue: Data Not Normalized

**Check 1**: Verify normalization is enabled
```bash
curl http://localhost:8080/api/normalization/status
```

**Check 2**: Check normalization errors in logs
```bash
docker logs iot-connector | grep "normalization_error"
```

**Check 3**: Verify source config has context
```yaml
sources:
  - name: "my_source"
    site_id: "columbus"  # Required for normalization
    line_id: "line3"     # Required for normalization
    equipment_id: "plc1" # Required for normalization
```

### Issue: Backpressure Queue Full

**Check**: Query queue stats
```bash
curl http://localhost:8080/api/stats
```

**Solutions**:
1. Increase queue size in config
2. Reduce batch timeout for faster draining
3. Check ZeroBus connection is stable
4. Enable disk spool for overflow

### Issue: Authentication Failed

**Error**: `OAuth2 token request failed`

**Solutions**:
1. Verify client ID and secret are correct
2. Check token endpoint URL matches workspace
3. Verify service principal has correct permissions:
   ```sql
   GRANT ALL PRIVILEGES ON CATALOG main TO `client-id`;
   GRANT ALL PRIVILEGES ON SCHEMA main.iot_bronze TO `client-id`;
   GRANT INSERT ON TABLE main.iot_bronze.normalized_tags TO `client-id`;
   ```

## Complete Example Configuration

Here's a complete working configuration:

**iot_connector/config/connector.yaml**:

```yaml
# Enable ZeroBus
zerobus:
  enabled: true
  workspace_host: "https://your-workspace.cloud.databricks.com"
  zerobus_endpoint: "your-endpoint.zerobus.region.cloud.databricks.com"

  auth:
    client_id: "${DATABRICKS_CLIENT_ID}"
    client_secret: "${DATABRICKS_CLIENT_SECRET}"
    token_endpoint: "https://your-workspace.cloud.databricks.com/oidc/v1/token"

  target:
    catalog: "main"
    schema: "iot_bronze"
    table: "normalized_tags"

  connection:
    timeout_seconds: 30
    max_retries: 3

  batch:
    max_records: 1000
    timeout_seconds: 5.0

# Protocol sources
sources:
  - name: "opcua_plc1"
    protocol: "opcua"
    enabled: true
    endpoint: "opc.tcp://localhost:4840"
    site_id: "columbus"
    line_id: "line3"
    equipment_id: "plc1"
    normalization_enabled: true

  - name: "mqtt_sensors"
    protocol: "mqtt"
    enabled: true
    endpoint: "mqtt://localhost:1883"
    site_id: "columbus"
    line_id: "line3"
    equipment_id: "press1"
    normalization_enabled: true
    topics: ["columbus/#"]

  - name: "modbus_conveyor"
    protocol: "modbus"
    enabled: true
    endpoint: "modbus://localhost:5020"
    site_id: "columbus"
    line_id: "line3"
    equipment_id: "conveyor1"
    normalization_enabled: true
    unit_id: 1
    registers:
      - type: "holding"
        address: 0
        count: 10

# Backpressure settings
backpressure:
  enabled: true
  memory_queue:
    max_size: 10000
    drop_policy: "oldest"
  disk_spool:
    enabled: true
    path: "spool"
    max_size_mb: 1000
```

**iot_connector/config/normalization_config.yaml**:

```yaml
mode: normalized

features:
  normalization_enabled: true

output:
  normalized_table: "main.iot_bronze.normalized_tags"
  raw_table: "main.iot_bronze.raw_protocol_data"
  write_both: false
```

## Summary

Once configured:

1. ✅ **Tag normalization** converts OPC-UA, MQTT, and Modbus data to unified schema
2. ✅ **Backpressure manager** queues records with disk spooling
3. ✅ **Batch processor** optimizes writes (1000 records or 5 seconds)
4. ✅ **ZeroBus client** writes to Databricks Unity Catalog via HTTP/2
5. ✅ **Delta tables** store normalized tags with partitioning and optimization
6. ✅ **Cross-protocol queries** enabled by unified schema

The normalized tags in Databricks are now ready for analytics, ML, and real-time dashboards!
