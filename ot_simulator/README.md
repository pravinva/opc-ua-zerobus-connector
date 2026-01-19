# OT Data Simulator

Professional-grade multi-protocol industrial sensor data simulator for testing IoT data ingestion pipelines.

## Overview

The OT Data Simulator generates realistic industrial sensor data for:
- **OPC-UA** - Server with 78 sensors across 4 industries
- **MQTT** - Publisher with JSON/Sparkplug B payloads
- **Modbus TCP/RTU** - Register-based data with scaling

### Industries Supported

| Industry | Sensors | Examples |
|----------|---------|----------|
| **Mining** | 16 | Crusher power/vibration, conveyor speed, ore flow |
| **Utilities** | 17 | Transformer load, grid frequency, battery voltage |
| **Manufacturing** | 18 | Robot torque, press force, assembly speed |
| **Oil & Gas** | 27 | Pipeline flow/pressure, compressor power, tank levels |

**Total: 78 realistic sensors** with appropriate ranges, units, and behavior patterns.

## Quick Start

### Installation

```bash
cd opc-ua-zerobus-connector
pip install -r requirements.txt
```

### Run All Simulators

```bash
# Start all enabled protocols from config
python -m ot_simulator

# Start with web UI
python -m ot_simulator --web-ui
```

### Run Specific Protocols

```bash
# OPC-UA only
python -m ot_simulator --protocol opcua

# MQTT only
python -m ot_simulator --protocol mqtt

# Modbus only
python -m ot_simulator --protocol modbus

# Multiple protocols
python -m ot_simulator --protocol mqtt --protocol modbus
```

### Custom Configuration

```bash
# Use custom config file
python -m ot_simulator --config my-config.yaml

# Override web port
python -m ot_simulator --web-ui --web-port 9000

# Debug logging
python -m ot_simulator --log-level DEBUG
```

## Configuration

### Default Config Location

`ot_simulator/config.yaml`

### Key Configuration Sections

#### Web UI

```yaml
web_ui:
  enabled: true
  host: "0.0.0.0"
  port: 8989  # Different from connector (8080)
  auto_open_browser: false
```

#### OPC-UA Server

```yaml
opcua:
  enabled: true
  endpoint: "opc.tcp://0.0.0.0:4840/ot-simulator/server/"
  server_name: "OT Data Simulator - OPC UA"
  namespace_uri: "http://databricks.com/iot-simulator"
  security_policy: "NoSecurity"
  update_rate_hz: 2.0
  industries:
    - mining
    - utilities
    - manufacturing
    - oil_gas
```

**Structure:**
- Root: `ns=2;s=Industries`
- Industries: `ns=2;s=Industries/{industry}`
- Sensors: `ns=2;s=Industries/{industry}/{sensor_name}`
- Metadata: `Unit`, `Type`, `Min`, `Max` properties

#### MQTT Publisher

```yaml
mqtt:
  enabled: true
  broker:
    host: "localhost"
    port: 1883
    use_tls: false
    tls_port: 8883
  auth:
    username: ""
    password: ""
  client_id: "ot-simulator-publisher"
  qos: 1
  topic_prefix: "sensors"
  payload_format: "json"  # json, string, sparkplug_b
  include_metadata: true
  include_timestamp: true
  publish_rate_hz: 2.0
  batch_publish: false
  industries:
    - mining
    - utilities
    - manufacturing
    - oil_gas
```

**Topics:**
- Individual: `sensors/{industry}/{sensor_name}/value`
- Metadata: `sensors/{industry}/{sensor_name}/metadata` (retained)
- Batch: `sensors/batch` (all sensors in one message)

**Payload Formats:**

1. **JSON** (default):
```json
{
  "value": 450.123,
  "unit": "kW",
  "timestamp": 1704724800000,
  "sensor_type": "power",
  "min": 200.0,
  "max": 800.0,
  "nominal": 450.0,
  "fault": false
}
```

2. **String**: `450.123`

3. **Sparkplug B** (simplified JSON structure):
```json
{
  "timestamp": 1704724800000,
  "metrics": [
    {
      "name": "crusher_1_motor_power",
      "timestamp": 1704724800000,
      "datatype": "Double",
      "value": 450.123,
      "properties": {
        "unit": "kW",
        "type": "power"
      }
    }
  ],
  "seq": 42
}
```

#### Modbus Server

```yaml
modbus:
  enabled: true
  tcp:
    enabled: true
    host: "0.0.0.0"
    port: 5020  # Non-privileged port (502 requires root)
  rtu:
    enabled: false
    port: "/dev/ttyUSB0"
    baudrate: 9600
    parity: "N"
    stopbits: 1
    bytesize: 8
  slave_id: 1
  register_mapping:
    mining:
      start_address: 0
    utilities:
      start_address: 1000
    manufacturing:
      start_address: 2000
    oil_gas:
      start_address: 3000
  scale_factor: 10  # Multiply values by 10 for integer storage
  update_rate_hz: 2.0
  industries:
    - mining
    - utilities
    - manufacturing
    - oil_gas
```

**Register Layout:**
- Mining: Addresses 0-15 (16 sensors)
- Utilities: Addresses 1000-1016 (17 sensors)
- Manufacturing: Addresses 2000-2017 (18 sensors)
- Oil & Gas: Addresses 3000-3026 (27 sensors)

**Value Scaling:**
- Raw value: `450.123 kW`
- Scaled value: `int(450.123 * 10) = 4501`
- To decode: `scaled_value / scale_factor = 4501 / 10 = 450.1`

#### Monitoring

```yaml
monitoring:
  prometheus:
    enabled: true
    port: 9091  # Different from connector (9090)
    path: "/metrics"
```

**Metrics Available:**
- `ot_simulator_sensors_total` - Total sensor count
- `ot_simulator_updates_total` - Update counter
- `ot_simulator_faults_active` - Active fault count

## Web UI

Start with `--web-ui` flag:

```bash
python -m ot_simulator --web-ui
```

Access at: **http://localhost:8989**

### Features

- **Dashboard** - View all simulator status
- **Protocol Control** - Start/stop individual protocols
- **Live Stats** - Sensor counts, update rates
- **Sensor Inventory** - Browse all 78 sensors
- **Fault Injection** - Inject faults via API (UI coming soon)

### API Endpoints

#### Health Check
```bash
curl http://localhost:8989/api/health
```

#### List Sensors
```bash
curl http://localhost:8989/api/sensors
```

#### Simulator Status
```bash
curl http://localhost:8989/api/simulators
```

#### Start/Stop Simulators
```bash
# Start OPC-UA
curl -X POST http://localhost:8989/api/simulators/opcua/start

# Stop MQTT
curl -X POST http://localhost:8989/api/simulators/mqtt/stop
```

#### Inject Fault
```bash
curl -X POST http://localhost:8989/api/fault/inject \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "opcua",
    "sensor_path": "mining/crusher_1_motor_power",
    "duration": 30.0
  }'
```

## Testing with Connector

### 1. Start Simulator

```bash
cd opc-ua-zerobus-connector
python -m ot_simulator --protocol all
```

**Output:**
```
2026-01-11 10:00:00 - ot_simulator - INFO - OPC-UA simulator started on opc.tcp://0.0.0.0:4840
2026-01-11 10:00:00 - ot_simulator - INFO - MQTT simulator started, publishing to localhost:1883
2026-01-11 10:00:00 - ot_simulator - INFO - Modbus TCP simulator started on 0.0.0.0:5020
2026-01-11 10:00:00 - ot_simulator - INFO - All simulators running. Press Ctrl+C to stop.
```

### 2. Configure Connector

Edit `config.yaml`:

```yaml
web_port: 8080
metrics_port: 9090

sources:
  - name: "simulator-opcua"
    endpoint: "opc.tcp://localhost:4840"
    protocol_type: "opcua"
    variable_limit: 20

  - name: "simulator-mqtt"
    endpoint: "mqtt://localhost:1883"
    protocol_type: "mqtt"
    mqtt:
      topics:
        - "sensors/mining/#"
        - "sensors/utilities/#"
      qos: 1

  - name: "simulator-modbus"
    endpoint: "modbus://localhost:5020"
    protocol_type: "modbus"
    modbus:
      slave_id: 1
      registers:
        - address: 0
          count: 16
          type: "holding"
      poll_interval_ms: 500

databricks:
  # ... your Databricks config
```

### 3. Start Connector

```bash
python -m opcua2uc --config config.yaml
```

### 4. Verify Data Flow

**Simulator UI:** http://localhost:8989
**Connector UI:** http://localhost:8080

**Check simulator metrics:**
```bash
curl http://localhost:9091/metrics | grep ot_simulator
```

**Check connector metrics:**
```bash
curl http://localhost:9090/metrics | grep opcua2uc
```

## Sensor Details

### List All Sensors

```bash
python -m ot_simulator --list-sensors
```

**Output:**
```
=== Available Sensors by Industry ===

MINING (16 sensors):
--------------------------------------------------------------------------------
  crusher_1_motor_power                         200.0 -    800.0 kW         [power]
  crusher_1_vibration_x                           1.0 -     25.0 mm/s       [vibration]
  crusher_1_vibration_y                           1.0 -     25.0 mm/s       [vibration]
  ...
```

### Sensor Characteristics

All sensors include:
- **Realistic ranges** - Based on industry standards
- **Noise** - Random fluctuations (configurable std dev)
- **Drift** - Gradual value changes over time
- **Cyclic patterns** - Sine wave variations for rotating equipment
- **Anomalies** - Random spike/dropout events (configurable probability)

### Fault Injection

Inject temporary faults for testing:

```python
# Via API
import requests
requests.post("http://localhost:8989/api/fault/inject", json={
    "protocol": "opcua",
    "sensor_path": "mining/crusher_1_motor_power",
    "duration": 30.0  # seconds
})
```

**Fault Behaviors:**
- Value goes outside normal range
- `fault` flag set to `true` in payloads
- Automatic recovery after duration expires

## Advanced Usage

### Custom Sensor Configuration

Override default sensor behavior in `config.yaml`:

```yaml
sensors:
  global_config:
    noise_multiplier: 2.0  # Double the noise
    drift_enabled: true
  mining:
    enabled: true
    sensors:
      crusher_1_motor_power:
        nominal_value: 500.0  # Override default
        noise_std: 20.0
```

### Port Conflicts

If default ports are unavailable:

```yaml
web_ui:
  port: 9000  # Changed from 8989

opcua:
  endpoint: "opc.tcp://0.0.0.0:4841/ot-simulator/server/"  # Changed from 4840

mqtt:
  broker:
    port: 1884  # Changed from 1883

modbus:
  tcp:
    port: 5021  # Changed from 5020

monitoring:
  prometheus:
    port: 9092  # Changed from 9091
```

See [PORTS.md](../PORTS.md) for comprehensive port management guide.

### Running in Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY ot_simulator/ ot_simulator/
COPY opcua2uc/ opcua2uc/

EXPOSE 8989 4840 1883 5020 9091

CMD ["python", "-m", "ot_simulator", "--protocol", "all"]
```

**Build and run:**
```bash
docker build -t ot-simulator .

docker run -d \
  --name ot-simulator \
  -p 8989:8989 \
  -p 4840:4840 \
  -p 1883:1883 \
  -p 5020:5020 \
  -p 9091:9091 \
  -v $(pwd)/ot_simulator/config.yaml:/app/ot_simulator/config.yaml \
  ot-simulator
```

## Troubleshooting

### OPC-UA Connection Refused

**Symptom:** Connector can't connect to `opc.tcp://localhost:4840`

**Solutions:**
1. Check simulator is running: `lsof -i :4840`
2. Verify endpoint in both configs matches
3. Try `127.0.0.1` instead of `localhost`
4. Check firewall: `sudo ufw allow 4840/tcp`

### MQTT Not Receiving Messages

**Symptom:** No messages on subscribed topics

**Solutions:**
1. Verify broker is running: `netstat -an | grep 1883`
2. Check topic prefix matches: `sensors/mining/#`
3. Verify QoS level compatibility
4. Test with mosquitto_sub:
```bash
mosquitto_sub -h localhost -t "sensors/#" -v
```

### Modbus Read Errors

**Symptom:** Connector reports Modbus read failures

**Solutions:**
1. Verify address ranges in connector config
2. Check slave ID matches (default: 1)
3. Ensure register count doesn't exceed available range
4. Test with modpoll:
```bash
modpoll -m tcp -a 1 -r 0 -c 16 localhost 5020
```

### Port Already in Use

**Symptom:** `Address already in use` error

**Solutions:**
1. Find conflicting process: `lsof -i :8989`
2. Kill it: `kill -9 <PID>`
3. Or change port in config (see Advanced Usage above)

### High CPU Usage

**Symptom:** Simulator consuming high CPU

**Solutions:**
1. Reduce update rates:
```yaml
opcua:
  update_rate_hz: 1.0  # Changed from 2.0

mqtt:
  publish_rate_hz: 1.0

modbus:
  update_rate_hz: 1.0
```

2. Disable unused protocols
3. Reduce sensor count by disabling industries

## Performance

### Resource Usage

**Per Protocol (78 sensors @ 2 Hz):**
- CPU: 5-10% (single core)
- Memory: 50-100 MB
- Network: ~100 KB/s

**All Protocols Combined:**
- CPU: 15-25%
- Memory: 150-250 MB
- Network: ~300 KB/s

### Scalability

**Tested Configurations:**
- ✅ 78 sensors @ 10 Hz (all protocols)
- ✅ 200 sensors @ 5 Hz (OPC-UA only)
- ✅ 1000 MQTT messages/sec

**Limitations:**
- OPC-UA: ~500 nodes with 10 Hz updates
- MQTT: Limited by broker capacity
- Modbus: Sequential polling, ~100 registers @ 10 Hz

## Examples

### Example 1: Mining Data Only

```yaml
opcua:
  enabled: true
  industries:
    - mining

mqtt:
  enabled: true
  industries:
    - mining

modbus:
  enabled: true
  industries:
    - mining
```

**Result:** 16 sensors across all protocols

### Example 2: High-Frequency Updates

```yaml
opcua:
  update_rate_hz: 10.0

mqtt:
  publish_rate_hz: 10.0

modbus:
  update_rate_hz: 10.0
```

**Result:** 10 updates/second per sensor

### Example 3: MQTT Batch Mode

```yaml
mqtt:
  batch_publish: true
  publish_rate_hz: 1.0
```

**Result:** Single message per second with all 78 sensor values

### Example 4: Testing Fault Scenarios

```python
import requests
import time

# Inject fault every 60 seconds
while True:
    requests.post("http://localhost:8989/api/fault/inject", json={
        "protocol": "opcua",
        "sensor_path": "utilities/grid_main_frequency",
        "duration": 30.0
    })
    time.sleep(60)
```

## Next Steps

1. **Connect to Real Broker/PLC**
   Use simulator as reference for real device integration

2. **Load Testing**
   Test connector throughput and backpressure handling

3. **Monitoring Setup**
   Configure Prometheus scraping of both simulator (9091) and connector (9090)

4. **Custom Sensors**
   Extend `sensor_models.py` with your own industries/sensors

5. **Protocol Extensions**
   Add support for other protocols (S7, EtherNet/IP, BACnet)

## Support

- **Documentation:** See [PROTOCOLS.md](../PROTOCOLS.md) for connector protocol guide
- **Configuration:** See [PORTS.md](../PORTS.md) for port management
- **Issues:** File issues at your repository

## License

Same as parent project (opc-ua-zerobus-connector)
