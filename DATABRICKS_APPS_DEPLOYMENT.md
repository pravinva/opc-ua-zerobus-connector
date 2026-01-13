# Deploying OT Simulator to Databricks Apps

This guide explains how to deploy the OT Protocol Simulator to Databricks Apps for easy demo access without requiring localhost.

## What You Can Deploy

You have **two deployment options**:

### Option 1: OT Simulator Only (Recommended for Demos)
Deploy just the simulator with its web UI showing real-time sensor data from all 3 protocols (OPC-UA, MQTT, Modbus).

**Features:**
- Interactive web dashboard at port 8989
- Real-time sensor visualization with charts
- Natural language control via LLM agent
- 80 sensors across 4 industries (mining, utilities, manufacturing, oil_gas)
- Live protocol servers (OPC-UA:4840, MQTT:1883, Modbus:5020)

**Use Case:** Perfect for demos where you want to show the data source side

### Option 2: Full Stack (Simulator + Connector)
Deploy both the simulator AND the IoT connector that writes to Unity Catalog via ZeroBus.

**Features:**
- Everything from Option 1
- Live ingestion to Unity Catalog tables
- End-to-end data flow visualization
- ZeroBus integration with OAuth2

**Use Case:** Complete E2E demo showing data generation → ingestion → Unity Catalog

---

## Option 1: Deploy OT Simulator to Databricks Apps

### Step 1: Create `app.yaml` for Simulator

Create this file at the project root:

```yaml
# app.yaml - OT Simulator Deployment
name: ot-protocol-simulator
description: Multi-protocol OT data simulator with real-time web UI (OPC-UA, MQTT, Modbus)

# Compute configuration
compute:
  type: serverless
  min_workers: 1
  max_workers: 1

# Environment
env:
  - name: PYTHONUNBUFFERED
    value: "1"
  - name: LOG_LEVEL
    value: "INFO"

# Port configuration
port: 8989

# Command to run
command: ["python", "-m", "ot_simulator", "--web-ui"]

# Dependencies
requirements:
  - asyncua==1.1.5
  - aiomqtt==2.0.1
  - pymodbus==3.6.4
  - aiohttp==3.9.0
  - pyyaml==6.0.1
  - databricks-sdk==0.18.0

# Health check (optional)
health_check:
  path: /
  interval: 30
  timeout: 5
```

### Step 2: Prepare the Deployment

On the **feature branch** (where the full simulator exists):

```bash
# Switch to feature branch
git checkout feature/standalone-dmz-connector

# Create a deployment directory
mkdir -p databricks_apps_deploy
cd databricks_apps_deploy

# Copy simulator files
cp -r ../ot_simulator .
cp ../requirements.txt .
cp ../app.yaml .

# Create a simple README
cat > README.md << 'EOF'
# OT Protocol Simulator - Databricks App

Multi-protocol industrial IoT data simulator.

## Access
- Web UI: https://<your-workspace>.cloud.databricks.com/apps/<app-id>/
- OPC-UA Server: Port 4840
- MQTT Broker: Port 1883
- Modbus Server: Port 5020

## Usage
The web UI provides:
- Real-time sensor data visualization
- Natural language control
- Protocol statistics
- Industry-specific sensor browsing
EOF
```

### Step 3: Deploy Using Databricks CLI

```bash
# Install Databricks CLI if not already installed
pip install databricks-cli

# Configure CLI (if not already done)
databricks configure --token

# Create the app
databricks apps create \
  --name "ot-protocol-simulator" \
  --source-code-path . \
  --config app.yaml

# Or use the UI:
# 1. Go to Workspace > Apps
# 2. Click "Create App"
# 3. Upload the deployment directory
# 4. Configure settings from app.yaml
```

### Step 4: Access Your App

Once deployed, you'll get a URL like:
```
https://e2-demo-field-eng.cloud.databricks.com/apps/12345678/
```

This will show the simulator web UI with:
- Real-time charts
- Natural language chat interface
- Protocol controls
- Sensor browser

---

## Option 2: Deploy Full Stack (Simulator + Connector)

### Step 1: Create `app.yaml` for Full Stack

```yaml
# app.yaml - Full Stack Deployment
name: ot-connector-demo
description: Complete IoT data flow - Simulator → Connector → Unity Catalog

compute:
  type: serverless
  min_workers: 1
  max_workers: 2

env:
  - name: PYTHONUNBUFFERED
    value: "1"
  - name: DATABRICKS_CLIENT_ID
    value: "{{secrets/iot-demo/client-id}}"
  - name: DATABRICKS_CLIENT_SECRET
    value: "{{secrets/iot-demo/client-secret}}"
  - name: CONNECTOR_MASTER_PASSWORD
    value: "{{secrets/iot-demo/master-password}}"

port: 8989

# Run both simulator and connector
command:
  - /bin/bash
  - -c
  - |
    # Start connector in background
    python -m connector --config connector_config.yaml &

    # Start simulator with web UI
    python -m ot_simulator --web-ui

requirements:
  - asyncua==1.1.5
  - aiomqtt==2.0.1
  - pymodbus==3.6.4
  - aiohttp==3.9.0
  - pyyaml==6.0.1
  - databricks-sdk==0.18.0
  - databricks-zerobus-ingest-sdk>=0.1.0
  - protobuf==4.25.1
  - grpcio-tools==1.60.0
  - cryptography==41.0.7

health_check:
  path: /
  interval: 60
  timeout: 10
```

### Step 2: Configure Secrets

```bash
# Create Databricks secret scope
databricks secrets create-scope --scope iot-demo

# Add OAuth credentials
databricks secrets put --scope iot-demo --key client-id
databricks secrets put --scope iot-demo --key client-secret
databricks secrets put --scope iot-demo --key master-password
```

### Step 3: Prepare Connector Config

Create `connector_config.yaml`:

```yaml
sources:
  - name: simulator_opcua
    endpoint: opc.tcp://localhost:4840
    protocol: opcua
    enabled: true

  - name: simulator_mqtt
    endpoint: mqtt://localhost:1883
    protocol: mqtt
    enabled: true

  - name: simulator_modbus
    endpoint: modbus://localhost:5020
    protocol: modbus
    enabled: true

zerobus:
  workspace_host: ${DATABRICKS_HOST}
  zerobus_endpoint: <your-zerobus-endpoint>.zerobus.us-west-2.cloud.databricks.com

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
  enabled: true
  host: 0.0.0.0
  port: 8080
```

### Step 4: Deploy

```bash
# Prepare deployment directory
mkdir -p databricks_apps_deploy_full
cd databricks_apps_deploy_full

# Copy all necessary files
cp -r ../ot_simulator .
cp -r ../connector .
cp -r ../protos .
cp ../requirements.txt .
cp ../app.yaml .
cp connector_config.yaml .

# Deploy
databricks apps create \
  --name "ot-connector-demo" \
  --source-code-path . \
  --config app.yaml
```

---

## Alternative: Databricks Jobs with Notebooks

If Databricks Apps aren't available, you can use Jobs with notebooks:

### 1. Create Notebook: `run_simulator.py`

```python
%pip install asyncua==1.1.5 aiomqtt==2.0.1 pymodbus==3.6.4 aiohttp==3.9.0

import subprocess
import sys

# Clone repo
!git clone https://github.com/your-org/opc-ua-zerobus-connector.git
%cd opc-ua-zerobus-connector
!git checkout feature/standalone-dmz-connector

# Run simulator
!python -m ot_simulator --web-ui
```

### 2. Create Job

```bash
databricks jobs create --json '{
  "name": "OT Simulator Demo",
  "tasks": [{
    "task_key": "run_simulator",
    "notebook_task": {
      "notebook_path": "/Users/your-email/run_simulator"
    },
    "cluster_spec": {
      "new_cluster": {
        "spark_version": "14.3.x-scala2.12",
        "node_type_id": "i3.xlarge",
        "num_workers": 0
      }
    }
  }],
  "schedule": {
    "quartz_cron_expression": "0 0 9 * * ?",
    "timezone_id": "America/Los_Angeles"
  }
}'
```

---

## Demo Flow Recommendations

### For Customer Demos:

1. **Pre-Demo Setup**
   - Deploy simulator to Databricks Apps
   - Share public URL with attendees
   - Pre-configure Unity Catalog tables

2. **Demo Flow**
   - Open simulator web UI (shared link)
   - Show real-time sensor data from all 3 protocols
   - Use natural language to control simulator
     - "Inject fault in mining conveyor belt speed"
     - "Show utilities turbine metrics"
   - Switch to Unity Catalog to show ingested data
   - Query data in SQL or notebooks

3. **Advantages Over Localhost**
   - ✅ No VPN required
   - ✅ No laptop dependencies
   - ✅ Accessible from any device
   - ✅ Always-on availability
   - ✅ Professional URL
   - ✅ Databricks-native hosting

---

## Troubleshooting

### Port Conflicts
If ports are already in use, modify `ot_simulator/config.yaml`:
```yaml
opcua:
  port: 14840  # Changed from 4840
mqtt:
  port: 11883  # Changed from 1883
modbus:
  port: 15020  # Changed from 5020
```

### Memory Issues
Increase compute resources in `app.yaml`:
```yaml
compute:
  type: custom
  instance_type: m5.xlarge
  min_workers: 1
  max_workers: 1
```

### Credential Issues
Verify secrets are accessible:
```bash
databricks secrets list --scope iot-demo
```

---

## Cost Considerations

**Simulator Only:**
- Serverless: ~$0.10/hour
- Single node m5.large: ~$0.20/hour

**Full Stack:**
- Serverless: ~$0.20/hour
- Single node m5.xlarge: ~$0.40/hour

**Recommendation:** Use "Run on Demand" for demos, not 24/7 hosting.

---

## Next Steps

1. Choose deployment option (Simulator only or Full Stack)
2. Create `app.yaml` file
3. Deploy using Databricks CLI or UI
4. Share URL with team for demos
5. Query Unity Catalog tables to verify data flow

For questions, see:
- Databricks Apps Docs: https://docs.databricks.com/apps/
- ZeroBus SDK: https://docs.databricks.com/ingestion/zerobus/
