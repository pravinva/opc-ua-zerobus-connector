# MQTT Broker Solution for Databricks Apps

## The Problem

The simulator currently tries to start an external **Mosquitto** broker (`mosquitto` command), which requires:
- System-level installation (`apt-get install mosquitto`)
- Not available in Databricks Apps (no root access)
- Cannot be installed via `requirements.txt`

## Three Solutions for Option 2 (Full Stack Deployment)

### Solution 1: Use External MQTT Broker (Recommended)

**Best for production demos** - Use a cloud MQTT broker instead of localhost.

#### Option A: HiveMQ Cloud (Free Tier)
```yaml
# In config.yaml
mqtt:
  broker:
    host: "your-cluster.s1.eu.hivemq.cloud"
    port: 8883
    use_tls: true
  auth:
    username: "your-username"
    password: "your-password"
```

**Setup:**
1. Sign up at https://console.hivemq.cloud/
2. Create free cluster (gets you: `xyz.s1.eu.hivemq.cloud:8883`)
3. Create credentials
4. Update simulator config

**Advantages:**
- ✅ Works perfectly in Databricks Apps
- ✅ No system dependencies
- ✅ Free tier available
- ✅ Professional hosting
- ✅ TLS encryption included

#### Option B: Eclipse Mosquitto Public Test Broker
```yaml
mqtt:
  broker:
    host: "test.mosquitto.org"
    port: 1883
```

**Advantages:**
- ✅ Zero configuration
- ✅ Works immediately
- ⚠️ Public (not for sensitive data)

### Solution 2: Use Pure Python MQTT Broker

**Embed a Python MQTT broker** - No system dependencies.

#### Update requirements.txt
```txt
# Add to requirements.txt
gmqtt==0.6.13          # Pure Python MQTT broker
```

#### Update app.yaml
```yaml
command:
  - /bin/bash
  - -c
  - |
    # Start embedded MQTT broker in background
    python -m ot_simulator.embedded_mqtt_broker &

    # Wait for broker to start
    sleep 2

    # Start connector in background
    python -m connector --config connector_config.yaml &

    # Start simulator with web UI
    python -m ot_simulator --web-ui
```

#### Create embedded_mqtt_broker.py
This would be a new file in `ot_simulator/` that runs gmqtt as a standalone broker.

**Advantages:**
- ✅ No external dependencies
- ✅ Pure Python solution
- ✅ Works in Databricks Apps
- ⚠️ Less battle-tested than Mosquitto

### Solution 3: Simplify to OPC-UA + Modbus Only

**Skip MQTT entirely** for the full stack deployment.

#### Update config.yaml
```yaml
# Disable MQTT
protocols:
  opcua:
    enabled: true
  mqtt:
    enabled: false  # Disable for Databricks Apps
  modbus:
    enabled: true
```

**Advantages:**
- ✅ No MQTT broker needed
- ✅ OPC-UA and Modbus work perfectly
- ✅ Still shows multi-protocol capability
- ⚠️ Loses MQTT demo (but that's okay)

---

## Recommended Approach

For **Databricks Apps deployment**, use:

### For Simulator-Only (Option 1)
**Current approach works** - Simulator can skip MQTT or use embedded broker.

### For Full Stack (Option 2)
**Use Solution 1A (HiveMQ Cloud)** - Most professional and reliable.

Here's the complete setup:

## Implementation: HiveMQ Cloud Solution

### Step 1: Sign Up for HiveMQ Cloud

1. Go to https://console.hivemq.cloud/
2. Sign up (free tier: 100 connections, 10GB/month)
3. Create cluster
4. Note your connection details:
   - Host: `abc123.s1.eu.hivemq.cloud`
   - Port: `8883` (TLS)
   - Username: Create in "Access Management"
   - Password: Create in "Access Management"

### Step 2: Update Simulator Config

Create `ot_simulator/config_databricks_apps.yaml`:

```yaml
# Databricks Apps configuration with cloud MQTT broker
global_config:
  log_level: INFO
  data_dir: /tmp/ot_simulator_data

industries:
  - mining
  - utilities
  - manufacturing
  - oil_gas

protocols:
  opcua:
    enabled: true
    port: 4840
    endpoint: opc.tcp://0.0.0.0:4840/opcua/server
    security_mode: None

  mqtt:
    enabled: true
    broker:
      host: "your-cluster.s1.eu.hivemq.cloud"
      port: 8883
      use_tls: true
    auth:
      username: "your-username"  # Or use {{secrets}}
      password: "your-password"  # Or use {{secrets}}
    topics:
      base: iot/scada
    industries:
      - mining
      - utilities
      - manufacturing
      - oil_gas

  modbus:
    enabled: true
    port: 5020
    host: 0.0.0.0
    slave_id: 1
```

### Step 3: Update app.yaml for Full Stack

```yaml
name: ot-connector-full-stack
description: Complete IoT data flow - Simulator → Connector → Unity Catalog with cloud MQTT

compute:
  type: serverless
  min_workers: 1
  max_workers: 1

env:
  - name: PYTHONUNBUFFERED
    value: "1"
  - name: DATABRICKS_CLIENT_ID
    value: "{{secrets/iot-demo/client-id}}"
  - name: DATABRICKS_CLIENT_SECRET
    value: "{{secrets/iot-demo/client-secret}}"
  - name: CONNECTOR_MASTER_PASSWORD
    value: "{{secrets/iot-demo/master-password}}"

  # Optional: MQTT credentials via secrets
  - name: MQTT_USERNAME
    value: "{{secrets/iot-demo/mqtt-username}}"
  - name: MQTT_PASSWORD
    value: "{{secrets/iot-demo/mqtt-password}}"

port: 8989

command:
  - /bin/bash
  - -c
  - |
    # Start connector in background (will connect to local OPC-UA, cloud MQTT, local Modbus)
    python -m connector --config connector_config.yaml &

    # Wait for connector to initialize
    sleep 3

    # Start simulator with web UI (uses cloud MQTT broker)
    python -m ot_simulator --web-ui --config config_databricks_apps.yaml

requirements:
  # Protocol libraries
  - asyncua==1.1.5
  - aiomqtt==2.0.1
  - pymodbus==3.6.4

  # Web framework
  - aiohttp==3.9.0

  # Config and utilities
  - pyyaml==6.0.1
  - databricks-sdk==0.18.0

  # ZeroBus and connector
  - databricks-zerobus-ingest-sdk>=0.1.0
  - protobuf==4.25.1
  - grpcio-tools==1.60.0
  - cryptography==41.0.7

health_check:
  path: /
  interval: 60
  timeout: 10
```

### Step 4: Update Connector Config

The connector needs to connect to the **cloud MQTT broker**:

```yaml
# connector_config.yaml
sources:
  - name: simulator_opcua
    endpoint: opc.tcp://localhost:4840
    protocol: opcua
    enabled: true

  - name: simulator_mqtt_cloud
    endpoint: mqtt://your-cluster.s1.eu.hivemq.cloud:8883
    protocol: mqtt
    use_tls: true
    username: ${MQTT_USERNAME}
    password: ${MQTT_PASSWORD}
    topics:
      - iot/scada/#
    enabled: true

  - name: simulator_modbus
    endpoint: modbus://localhost:5020
    protocol: modbus
    enabled: true

zerobus:
  workspace_host: ${DATABRICKS_HOST}
  zerobus_endpoint: <your-endpoint>.zerobus.us-west-2.cloud.databricks.com

  auth:
    client_id: ${DATABRICKS_CLIENT_ID}
    client_secret: ${DATABRICKS_CLIENT_SECRET}

  target:
    catalog: main
    schema: scada_data
    table: iot_events_bronze

backpressure:
  max_queue_size: 10000
  spool_enabled: true
  spool_path: /tmp/spool

web_gui:
  enabled: false  # Simulator has the GUI
```

### Step 5: Deploy

```bash
# Add MQTT secrets
databricks secrets put --scope iot-demo --key mqtt-username
databricks secrets put --scope iot-demo --key mqtt-password

# Deploy full stack
./deploy_to_databricks_apps.sh full
```

---

## Architecture: Full Stack with Cloud MQTT

```
┌─────────────────────────────────────────────────────────┐
│              Databricks Apps Container                   │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │         OT Simulator (Port 8989 Web UI)        │    │
│  │                                                 │    │
│  │  ┌─────────────┐  ┌─────────────┐             │    │
│  │  │  OPC-UA     │  │   Modbus    │             │    │
│  │  │  Server     │  │   Server    │             │    │
│  │  │  Port 4840  │  │  Port 5020  │             │    │
│  │  └──────┬──────┘  └──────┬──────┘             │    │
│  │         │                │                      │    │
│  │         └────────┬───────┘                      │    │
│  │                  │                              │    │
│  │  ┌───────────────▼────────────────────┐        │    │
│  │  │      MQTT Publisher                │        │    │
│  │  │  → HiveMQ Cloud (external)         │────┐   │    │
│  │  └────────────────────────────────────┘    │   │    │
│  └────────────────────────────────────────────┘   │   │
│                                                    │   │
│  ┌─────────────────────────────────────────────┐  │   │
│  │         IoT Connector                       │  │   │
│  │                                             │  │   │
│  │  ┌──────────────────────────────────────┐  │  │   │
│  │  │     Protocol Clients                 │  │  │   │
│  │  │  • OPC-UA → localhost:4840           │  │  │   │
│  │  │  • Modbus → localhost:5020           │  │  │   │
│  │  │  • MQTT   → HiveMQ Cloud ◄───────────┼──┼──┘   │
│  │  └──────────────┬───────────────────────┘  │      │
│  │                 │                           │      │
│  │  ┌──────────────▼───────────────────────┐  │      │
│  │  │     ZeroBus SDK (Protobuf)           │  │      │
│  │  └──────────────┬───────────────────────┘  │      │
│  └─────────────────┼──────────────────────────┘      │
│                    │                                  │
└────────────────────┼──────────────────────────────────┘
                     │ HTTPS/443
                     ▼
         ┌───────────────────────┐
         │  Unity Catalog        │
         │  Bronze Tables        │
         └───────────────────────┘
```

---

## Summary

**Best approach for Databricks Apps full stack:**

1. ✅ Use **HiveMQ Cloud** (free tier) for MQTT broker
2. ✅ Keep OPC-UA and Modbus running locally in container
3. ✅ Connector reads from all 3 sources
4. ✅ Everything writes to Unity Catalog via ZeroBus
5. ✅ Web UI shows all data streams

**No system dependencies needed** - everything via Python packages!

**Cost:** HiveMQ free tier + Databricks Apps serverless (~$0.20/hour)
