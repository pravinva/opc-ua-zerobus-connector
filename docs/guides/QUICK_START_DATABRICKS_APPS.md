# Quick Start: Deploy to Databricks Apps

## TL;DR - 3 Commands to Deploy

```bash
# 1. Switch to feature branch (where full simulator exists)
git checkout feature/standalone-dmz-connector

# 2. Run deployment script
./deploy_to_databricks_apps.sh simulator

# 3. Access your app
# You'll get a URL like: https://<workspace>.cloud.databricks.com/apps/<app-id>/
```

---

## What Gets Deployed

**OT Protocol Simulator** - A web application that simulates industrial IoT sensors across 3 protocols:

- **Web UI**: Real-time dashboard with charts and controls
- **OPC-UA Server**: Port 4840 (80 sensors)
- **MQTT Broker**: Port 1883 (pub/sub topics)
- **Modbus Server**: Port 5020 (holding registers)

**Features:**
- 80 sensors across 4 industries (mining, utilities, manufacturing, oil & gas)
- Natural language control: "Inject fault in conveyor belt"
- Real-time visualization with Chart.js
- Protocol statistics and health monitoring

---

## Prerequisites

1. **Databricks CLI** installed:
   ```bash
   pip install databricks-cli
   ```

2. **Databricks CLI** configured:
   ```bash
   databricks configure --token
   ```

3. **On the correct branch**:
   ```bash
   git checkout feature/standalone-dmz-connector
   ```

---

## Deployment Methods

### Method 1: Automated Script (Recommended)

```bash
# Deploy simulator only (for demos)
./deploy_to_databricks_apps.sh simulator

# Or deploy full stack (simulator + connector writing to UC)
./deploy_to_databricks_apps.sh full
```

### Method 2: Manual CLI

```bash
# From project root
databricks apps create \
  --name ot-protocol-simulator \
  --source-code-path . \
  --config app.yaml
```

### Method 3: Databricks UI

1. Go to **Workspace > Apps**
2. Click **Create App**
3. Upload project files
4. Configure using settings from `app.yaml`
5. Click **Deploy**

---

## After Deployment

### Get Your App URL

```bash
# List all apps
databricks apps list

# Get specific app details
databricks apps get ot-protocol-simulator
```

You'll receive a URL like:
```
https://e2-demo-field-eng.cloud.databricks.com/apps/12345678/
```

### View Logs

```bash
# Stream logs
databricks apps logs ot-protocol-simulator --follow

# Get recent logs
databricks apps logs ot-protocol-simulator --tail 100
```

### Check Status

```bash
databricks apps get ot-protocol-simulator
```

---

## Demo Flow

1. **Share the URL** with your audience before the demo
2. **Open the Web UI** - shows real-time sensor data
3. **Navigate the interface:**
   - View real-time charts (2-minute rolling window)
   - Browse sensors by industry
   - Use natural language chat: "Show mining conveyor belt metrics"
   - Monitor protocol statistics
4. **Inject faults** to show anomaly detection
5. **Query Unity Catalog** (if using full stack mode) to show ingested data

---

## Cost Optimization

**Serverless Pricing** (~$0.10/hour):
- Best for demos and testing
- Auto-scales to zero when not in use

**Always-On for Demos:**
```yaml
compute:
  type: serverless
  min_workers: 1
  max_workers: 1
```

**On-Demand for Dev:**
- Stop after each demo
- Start 10 minutes before next demo

**Commands:**
```bash
# Stop app
databricks apps stop ot-protocol-simulator

# Start app
databricks apps start ot-protocol-simulator
```

---

## Troubleshooting

### App Won't Start

**Check logs:**
```bash
databricks apps logs ot-protocol-simulator --tail 200
```

**Common issues:**
- Missing dependencies: Check `requirements.txt`
- Port conflicts: Verify ports 4840, 1883, 5020, 8989 are available
- Memory limits: Increase in `app.yaml`

### Can't Access Web UI

**Verify app status:**
```bash
databricks apps get ot-protocol-simulator
```

**Check health:**
- App should show status: `RUNNING`
- Health check should be passing
- URL should be accessible (may take 1-2 minutes after start)

### Missing Data in Charts

**Check simulator status:**
- Open browser console (F12)
- Look for WebSocket connection errors
- Verify JavaScript is enabled

---

## Advanced: Full Stack Deployment

To deploy the complete end-to-end solution (simulator + connector + ZeroBus writes):

### 1. Create Databricks Secrets

```bash
# Create secret scope
databricks secrets create-scope --scope iot-demo

# Add OAuth credentials
databricks secrets put --scope iot-demo --key client-id
databricks secrets put --scope iot-demo --key client-secret
databricks secrets put --scope iot-demo --key master-password
```

### 2. Update app.yaml

Uncomment the environment variables section:
```yaml
env:
  - name: DATABRICKS_CLIENT_ID
    value: "{{secrets/iot-demo/client-id}}"
  - name: DATABRICKS_CLIENT_SECRET
    value: "{{secrets/iot-demo/client-secret}}"
```

### 3. Deploy

```bash
./deploy_to_databricks_apps.sh full
```

This deploys both:
- Simulator generating data on localhost
- Connector reading from simulator and writing to Unity Catalog

---

## Demo Script Template

**Opening (1 min):**
> "Today I'll show you how Databricks ingests industrial IoT data from multiple protocols. I've deployed a simulator to Databricks Apps so you can follow along."

**Show Simulator (2 min):**
> "Here's our simulator running 80 sensors across OPC-UA, MQTT, and Modbus. Let me show you real-time data from a mining conveyor belt..."
>
> [Navigate to mining sensors, show live charts]

**Natural Language Control (1 min):**
> "We can control this via natural language. Watch what happens when I say: 'Inject fault in conveyor belt speed'"
>
> [Chart shows anomaly]

**Data Flow (2 min):**
> "This data flows through our connector to Unity Catalog. Let me show you the ingested data..."
>
> [Switch to SQL notebook, query bronze tables]

**Closing:**
> "All of this is running on Databricks serverless compute, costing less than $0.10/hour. The simulator URL is available 24/7 for your team to explore."

---

## Next Steps

1. ✅ Deploy simulator to Databricks Apps
2. ✅ Share URL with your team
3. ⏭️ Set up Unity Catalog tables for data ingestion
4. ⏭️ Deploy full stack with ZeroBus connector
5. ⏭️ Create dashboards visualizing ingested data

**Documentation:**
- Full deployment guide: `DATABRICKS_APPS_DEPLOYMENT.md`
- Connector setup: `databricks_iot_connector/README.md`
- Simulator details: `ot_simulator/README.md`

**Support:**
- Databricks Apps docs: https://docs.databricks.com/apps/
- File issues: https://github.com/your-org/repo/issues
