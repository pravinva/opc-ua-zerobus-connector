#!/bin/bash
# Deploy OT Simulator to Databricks Apps
# Usage: ./deploy_to_databricks_apps.sh [simulator|full]

set -e

MODE=${1:-simulator}
APP_NAME="ot-protocol-simulator"
DEPLOY_DIR="databricks_apps_deploy"

echo "=================================="
echo "Databricks Apps Deployment Script"
echo "=================================="
echo "Mode: $MODE"
echo ""

# Check if on correct branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$MODE" = "simulator" ] && [ "$CURRENT_BRANCH" != "feature/standalone-dmz-connector" ]; then
    echo "⚠️  Warning: You should be on feature/standalone-dmz-connector branch"
    echo "   Current branch: $CURRENT_BRANCH"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Clean up old deployment directory
echo "📁 Cleaning up old deployment directory..."
rm -rf $DEPLOY_DIR
mkdir -p $DEPLOY_DIR

# Copy necessary files based on mode
if [ "$MODE" = "simulator" ]; then
    echo "📦 Preparing simulator-only deployment..."

    # Copy simulator files
    cp -r ot_simulator $DEPLOY_DIR/
    cp requirements.txt $DEPLOY_DIR/
    cp app.yaml $DEPLOY_DIR/

    # Create minimal README
    cat > $DEPLOY_DIR/README.md << 'EOF'
# OT Protocol Simulator - Databricks App

Multi-protocol industrial IoT data simulator with real-time web UI.

## Protocols
- OPC-UA Server: Port 4840
- MQTT Broker: Port 1883
- Modbus Server: Port 5020
- Web UI: Port 8989

## Features
- 80 sensors across 4 industries
- Real-time charts and visualization
- Natural language control (if LLM configured)
- Protocol statistics and monitoring
EOF

elif [ "$MODE" = "full" ]; then
    echo "📦 Preparing full stack deployment (simulator + connector)..."

    # Copy all files
    cp -r ot_simulator $DEPLOY_DIR/
    cp -r connector $DEPLOY_DIR/
    cp -r protos $DEPLOY_DIR/
    cp requirements.txt $DEPLOY_DIR/
    cp app_full_stack.yaml $DEPLOY_DIR/app.yaml

    # Create connector config
    cat > $DEPLOY_DIR/connector_config.yaml << 'EOF'
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
EOF

    APP_NAME="ot-connector-full-stack"
else
    echo "❌ Invalid mode: $MODE"
    echo "   Usage: $0 [simulator|full]"
    exit 1
fi

echo "✅ Deployment directory prepared: $DEPLOY_DIR"
echo ""

# Check if databricks CLI is installed
if ! command -v databricks &> /dev/null; then
    echo "⚠️  Databricks CLI not found"
    echo ""
    echo "Install with: pip install databricks-cli"
    echo ""
    echo "Then configure: databricks configure --token"
    echo ""
    exit 1
fi

# Check if configured
if ! databricks workspace ls / &> /dev/null; then
    echo "⚠️  Databricks CLI not configured"
    echo ""
    echo "Configure with: databricks configure --token"
    echo ""
    exit 1
fi

echo "🚀 Ready to deploy!"
echo ""
echo "Deployment options:"
echo ""
echo "1. Deploy via CLI:"
echo "   cd $DEPLOY_DIR"
echo "   databricks apps create --name $APP_NAME --source-code-path . --config app.yaml"
echo ""
echo "2. Deploy via UI:"
echo "   - Go to Workspace > Apps > Create App"
echo "   - Upload the $DEPLOY_DIR directory"
echo "   - Use settings from app.yaml"
echo ""
echo "3. Deploy using Databricks Asset Bundles (DABs):"
echo "   - See DATABRICKS_APPS_DEPLOYMENT.md for DABs configuration"
echo ""

read -p "Deploy now via CLI? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🚀 Deploying to Databricks Apps..."
    cd $DEPLOY_DIR

    # Deploy
    databricks apps create \
        --name "$APP_NAME" \
        --source-code-path . \
        --config app.yaml

    echo ""
    echo "✅ Deployment complete!"
    echo ""
    echo "Check status:"
    echo "  databricks apps list"
    echo ""
    echo "View logs:"
    echo "  databricks apps logs $APP_NAME"
    echo ""
    echo "Get URL:"
    echo "  databricks apps get $APP_NAME"
else
    echo ""
    echo "✅ Deployment files ready in: $DEPLOY_DIR"
    echo "   Deploy manually when ready."
fi

echo ""
echo "=================================="
echo "📚 Documentation: DATABRICKS_APPS_DEPLOYMENT.md"
echo "=================================="
