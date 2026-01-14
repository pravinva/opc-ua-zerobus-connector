# Deployment Checklist for Databricks Apps

## Pre-Deployment Setup

### 1. HiveMQ Cloud Configuration ✅ DONE
- [x] Cluster: `fac4430cb2214735a5d8088af6d88519.s1.eu.hivemq.cloud`
- [x] Port: `8883` (TLS)
- [x] Username: `pravinva`
- [ ] Password: Need to add to Databricks secrets

### 2. Databricks Secrets Setup

Create the secret scope (if not exists):
```bash
databricks secrets create-scope --scope iot-demo
```

Add all required secrets:
```bash
# HiveMQ MQTT password
databricks secrets put --scope iot-demo --key mqtt-password
# Enter your HiveMQ password when prompted

# Databricks workspace host
databricks secrets put --scope iot-demo --key workspace-host
# Enter: https://e2-demo-field-eng.cloud.databricks.com

# Service Principal for ZeroBus (OAuth2 M2M)
databricks secrets put --scope iot-demo --key client-id
# Enter your Service Principal client ID

databricks secrets put --scope iot-demo --key client-secret
# Enter your Service Principal client secret

# ZeroBus endpoint
databricks secrets put --scope iot-demo --key zerobus-endpoint
# Enter: https://<your-endpoint>.zerobus.us-west-2.cloud.databricks.com

# Connector master password (for credential encryption)
databricks secrets put --scope iot-demo --key master-password
# Enter a strong password (e.g., generated: openssl rand -base64 32)
```

### 3. Service Principal Setup

If you don't have a Service Principal yet:

```bash
# Create Service Principal
databricks service-principals create \
  --display-name "IoT Connector Service Principal"

# Note the client_id from output
# Create client secret
databricks service-principals create-secret \
  --id <client-id>

# Note the client_secret from output
```

Grant permissions to Unity Catalog:
```sql
-- Run in SQL workspace
GRANT CREATE TABLE ON SCHEMA main.scada_data
TO SERVICE_PRINCIPAL '<client-id>';

GRANT INSERT ON TABLE main.scada_data.iot_events_bronze
TO SERVICE_PRINCIPAL '<client-id>';
```

### 4. Unity Catalog Tables Setup

Create the schema and bronze table:
```sql
-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS main.scada_data
COMMENT 'Industrial IoT sensor data from OT protocols';

-- Create bronze table for multi-protocol data
CREATE TABLE IF NOT EXISTS main.scada_data.iot_events_bronze (
  -- Timestamps
  event_time TIMESTAMP,
  ingest_time TIMESTAMP,

  -- Source identification
  source_name STRING,
  protocol STRING,

  -- Common fields
  sensor_name STRING,
  sensor_value DOUBLE,
  sensor_unit STRING,
  sensor_type STRING,

  -- Industry context
  industry STRING,

  -- PLC information
  plc_name STRING,
  plc_vendor STRING,
  plc_model STRING,

  -- Protocol-specific data (struct)
  opcua_data STRUCT<
    endpoint STRING,
    namespace INT,
    node_id STRING,
    browse_path STRING,
    status_code BIGINT,
    status STRING,
    value_type STRING
  >,

  mqtt_data STRUCT<
    topic STRING,
    qos INT,
    retain BOOLEAN,
    broker STRING
  >,

  modbus_data STRUCT<
    slave_id INT,
    register_address INT,
    register_type STRING,
    raw_value DOUBLE,
    scaled_value DOUBLE,
    scale_factor DOUBLE
  >,

  -- Raw payload
  raw_payload BINARY
)
USING DELTA
PARTITIONED BY (DATE(event_time), protocol)
COMMENT 'Bronze layer: Raw industrial IoT data from all protocols';
```

---

## Deployment Steps

### Option 1: Simulator Only (Quick Demo)

```bash
# Use default app.yaml
databricks apps create \
  --name ot-simulator \
  --source-code-path . \
  --config app.yaml
```

### Option 2: Full Stack (Simulator + Connector + ZeroBus)

```bash
# Use full stack configuration
databricks apps create \
  --name ot-connector-full \
  --source-code-path . \
  --config app_full_stack.yaml
```

---

## Post-Deployment Verification

### 1. Check App Status

```bash
# List apps
databricks apps list

# Get specific app details
databricks apps get ot-connector-full

# Expected output should show:
# - status: RUNNING
# - url: https://...cloud.databricks.com/apps/<id>/
```

### 2. View Logs

```bash
# Stream logs in real-time
databricks apps logs ot-connector-full --follow

# Look for:
# ✓ "Simulator started"
# ✓ "Connector started"
# ✓ "ZeroBus client initialized"
# ✓ "Web UI running on http://0.0.0.0:8989"
```

### 3. Access Web UI

Open the app URL in browser:
```
https://e2-demo-field-eng.cloud.databricks.com/apps/<app-id>/
```

You should see:
- Real-time sensor charts
- Protocol statistics (OPC-UA, MQTT, Modbus)
- Natural language chat interface
- Sensor browser by industry

### 4. Verify MQTT Connection

Check logs for HiveMQ connection:
```bash
databricks apps logs ot-connector-full | grep -i mqtt

# Expected:
# "MQTT client connected to fac4430cb2214735a5d8088af6d88519.s1.eu.hivemq.cloud:8883"
# "MQTT publisher started"
```

### 5. Verify ZeroBus Writes

Query Unity Catalog to see data:
```sql
-- Check row count
SELECT COUNT(*) as total_events
FROM main.scada_data.iot_events_bronze;

-- Check recent data by protocol
SELECT
  protocol,
  COUNT(*) as event_count,
  MAX(event_time) as latest_event
FROM main.scada_data.iot_events_bronze
GROUP BY protocol
ORDER BY protocol;

-- Sample recent events
SELECT *
FROM main.scada_data.iot_events_bronze
ORDER BY event_time DESC
LIMIT 10;
```

### 6. Monitor Data Ingestion Rate

```sql
-- Events per minute by protocol
SELECT
  protocol,
  DATE_TRUNC('minute', event_time) as minute,
  COUNT(*) as events_per_minute
FROM main.scada_data.iot_events_bronze
WHERE event_time >= CURRENT_TIMESTAMP - INTERVAL 10 MINUTES
GROUP BY protocol, DATE_TRUNC('minute', event_time)
ORDER BY minute DESC, protocol;
```

---

## Troubleshooting

### App Won't Start

**Check logs:**
```bash
databricks apps logs ot-connector-full --tail 200
```

**Common issues:**

1. **Missing secrets:**
   ```
   Error: Secret not found: iot-demo/mqtt-password
   ```
   **Fix:** Add the missing secret

2. **Invalid OAuth credentials:**
   ```
   Error: Invalid client_id or client_secret
   ```
   **Fix:** Verify Service Principal credentials

3. **ZeroBus endpoint not found:**
   ```
   Error: Failed to connect to ZeroBus endpoint
   ```
   **Fix:** Verify ZeroBus endpoint URL in secrets

### MQTT Connection Fails

**Check HiveMQ Cloud:**
1. Log in to https://console.hivemq.cloud/
2. Verify cluster is running
3. Check credentials are correct
4. Verify TLS is enabled

**Test connection locally:**
```bash
# Install mosquitto clients
pip install paho-mqtt

# Test publish
python -c "
import paho.mqtt.client as mqtt
import ssl

client = mqtt.Client()
client.username_pw_set('pravinva', '<your-password>')
client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)
client.connect('fac4430cb2214735a5d8088af6d88519.s1.eu.hivemq.cloud', 8883)
client.publish('test/topic', 'hello')
print('✓ MQTT connection successful')
"
```

### No Data in Unity Catalog

**Check connector is running:**
```bash
databricks apps logs ot-connector-full | grep "Connector started"
```

**Verify Service Principal permissions:**
```sql
SHOW GRANTS ON TABLE main.scada_data.iot_events_bronze;
```

**Check ZeroBus logs:**
```bash
databricks apps logs ot-connector-full | grep -i zerobus
```

### Web UI Not Accessible

**Verify app is running:**
```bash
databricks apps get ot-connector-full
# status should be RUNNING
```

**Check port configuration:**
```bash
databricks apps logs ot-connector-full | grep "8989"
# Should show: "Web UI running on http://0.0.0.0:8989"
```

---

## Configuration Files Used

- ✅ `app_full_stack.yaml` - Databricks Apps configuration
- ✅ `config_databricks_apps.yaml` - Simulator configuration with HiveMQ
- ✅ `connector_config_databricks_apps.yaml` - Connector configuration

All files configured with:
- HiveMQ Cloud: `fac4430cb2214735a5d8088af6d88519.s1.eu.hivemq.cloud:8883`
- Username: `pravinva`
- Password: From Databricks secrets

---

## Quick Commands Reference

```bash
# Deploy
databricks apps create --name ot-connector-full --source-code-path . --config app_full_stack.yaml

# Status
databricks apps get ot-connector-full

# Logs
databricks apps logs ot-connector-full --follow

# Stop
databricks apps stop ot-connector-full

# Start
databricks apps start ot-connector-full

# Delete
databricks apps delete ot-connector-full

# List secrets
databricks secrets list --scope iot-demo
```

---

## Next Steps After Deployment

1. ✅ Verify app is running
2. ✅ Access web UI
3. ✅ Confirm MQTT connection to HiveMQ
4. ✅ Verify data in Unity Catalog
5. ⏭️ Create downstream silver/gold tables
6. ⏭️ Build dashboards on ingested data
7. ⏭️ Set up monitoring and alerts
