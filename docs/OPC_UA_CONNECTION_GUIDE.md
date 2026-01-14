# OPC-UA Server Connection Guide

## Server Details

- **Endpoint URL**: `opc.tcp://localhost:4840/ot-simulator/server/`
- **Security Policy**: None (Anonymous)
- **Namespace URI**: `http://databricks.com/iot-simulator`
- **Total Sensors**: 347 sensors across 15 industries

## Connection Instructions

### 1. Ignition SCADA

**Steps:**
1. Navigate to **Config → OPC UA → Connections**
2. Click **Create new OPC UA Connection**
3. Fill in the details:
   - **Connection Name**: `OT Simulator`
   - **Endpoint URL**: `opc.tcp://localhost:4840/ot-simulator/server/`
   - **Security Policy**: `None`
   - **Authentication**: `Anonymous`
4. Click **Create New Connection**
5. **Enable** the connection
6. Browse tags in **Tag Browser** → expand the connection to see all 347 sensors

**Tag Structure in Ignition:**
```
OT Simulator/
├── IndustrialSensors/
    ├── mining/
    │   ├── conveyor_belt_1_speed
    │   ├── crusher_1_motor_power
    │   └── ...
    ├── utilities/
    │   ├── generator_1_output_power
    │   ├── transformer_1_temperature
    │   └── ...
    ├── manufacturing/
    ├── oil_gas/
    ├── aerospace/
    ├── space/
    ├── water_wastewater/
    ├── electric_power/
    ├── automotive/
    ├── chemical/
    ├── food_beverage/
    ├── pharmaceutical/
    ├── data_center/
    ├── smart_building/
    └── agriculture/
```

### 2. Prosys OPC UA Browser

**Steps:**
1. Open **Prosys OPC UA Browser**
2. Click **Connect** (or the connection dropdown)
3. **Endpoint URL**: `opc.tcp://localhost:4840/ot-simulator/server/`
4. **Security Mode**: `None`
5. **User Authentication**: `Anonymous`
6. Click **OK** to connect
7. Browse the **Address Space** tree to see all sensors

### 3. UaExpert (Unified Automation)

**Steps:**
1. Open **UaExpert**
2. Right-click **Servers** → **Add** → **Add Server...**
3. In **Custom Discovery**:
   - **URL**: `opc.tcp://localhost:4840/ot-simulator/server/`
4. Click **Get Endpoints**
5. Select the endpoint with Security Policy: `None`
6. Click **OK**
7. Double-click the server to connect
8. Browse the **Address Space** pane to see all sensors

### 4. Python (asyncua library)

```python
import asyncio
from asyncua import Client

async def main():
    url = "opc.tcp://localhost:4840/ot-simulator/server/"

    async with Client(url=url) as client:
        print("Connected to OPC-UA server")

        # Get root node
        root = client.get_root_node()
        objects = await root.get_child(["0:Objects"])

        # Navigate to IndustrialSensors
        industrial_sensors = await objects.get_child(["2:IndustrialSensors"])

        # Get mining sensors
        mining = await industrial_sensors.get_child(["2:mining"])

        # Read a specific sensor
        crusher_power = await mining.get_child(["2:crusher_1_motor_power"])
        value = await crusher_power.read_value()
        print(f"Crusher Motor Power: {value} kW")

        # List all children
        children = await mining.get_children()
        for child in children:
            name = await child.read_browse_name()
            val = await child.read_value()
            print(f"{name.Name}: {val}")

asyncio.run(main())
```

### 5. Node-RED (OPC-UA Client)

**Steps:**
1. Install the `node-red-contrib-opcua` package
2. Drag an **OPC UA-Client** node to your flow
3. Configure the client:
   - **Endpoint**: `opc.tcp://localhost:4840/ot-simulator/server/`
   - **Security Policy**: `None`
   - **Security Mode**: `None`
4. Use **OPC UA-Read** nodes to read sensor values
5. **Node ID** format: `ns=2;s=mining/crusher_1_motor_power`

### 6. FactoryIO

**Steps:**
1. Open **Factory I/O**
2. Go to **File → Drivers → Configuration**
3. Select **OPC UA Client**
4. **Server URL**: `opc.tcp://localhost:4840/ot-simulator/server/`
5. Click **Connect**
6. Map tags to your Factory I/O sensors/actuators

## Sensor Naming Convention

All sensors follow the pattern: `{industry}/{sensor_name}`

**Examples:**
- `mining/conveyor_belt_1_speed`
- `utilities/generator_1_output_power`
- `manufacturing/assembly_line_1_speed`
- `oil_gas/pipeline_1_flow`
- `aerospace/wind_tunnel_pressure`
- `water_wastewater/influent_ph`
- `data_center/rack_1_temperature`

## Available Industries

1. **mining** - 24 sensors (conveyors, crushers, pumps, drills, trucks)
2. **utilities** - 18 sensors (generators, transformers, substations)
3. **manufacturing** - 21 sensors (assembly lines, robots, CNCs, presses)
4. **oil_gas** - 15 sensors (pipelines, wells, compressors, tanks)
5. **aerospace** - 23 sensors (wind tunnels, autoclaves, test stands)
6. **space** - 29 sensors (vacuum chambers, thrusters, solar panels, gyroscopes)
7. **water_wastewater** - 28 sensors (influent/effluent, clarifiers, aeration, pumps)
8. **electric_power** - 24 sensors (turbines, generators, switchgear, capacitors)
9. **automotive** - 24 sensors (paint booths, welding, stamping, AGVs)
10. **chemical** - 27 sensors (reactors, distillation, crystallizers, filters)
11. **food_beverage** - 27 sensors (fermentation, pasteurization, bottling, mixers)
12. **pharmaceutical** - 30 sensors (bioreactors, autoclaves, lyophilizers, blenders)
13. **data_center** - 24 sensors (servers, cooling, UPS, generators)
14. **smart_building** - 24 sensors (HVAC, lighting, elevators, access control)
15. **agriculture** - 29 sensors (irrigation, greenhouses, grain storage, tractors)

## Troubleshooting

### Connection Refused
- Ensure the simulator is running: `python -m ot_simulator --protocol opcua --web-ui`
- Check the simulator logs: `tail -f ot_simulator.log`
- Verify port 4840 is not blocked by firewall

### No Data Visible
- The simulator needs to be **started** (either via Web UI or NLP command)
- Use NLP command: "start opcua"
- Or click the **Start** button next to OPC-UA in the Web UI
- Check Web UI at http://localhost:8989 to verify status

### Sensors Not Updating
- Sensors update at **2 Hz** (every 500ms) by default
- Check if OPC-UA simulator shows "running" status in Web UI
- Look for "OPC-UA server started" message in logs

### Bad_Timeout or Connection Errors from Ignition/Clients
If you get "Bad_Timeout" or "TypeError: issubclass() arg 1 must be a class" errors:

**Root Cause**: Python 3.14 has compatibility issues with asyncua library

**Solution**: Downgrade to Python 3.11 or 3.12
```bash
# Using pyenv (recommended)
pyenv install 3.12.0
pyenv local 3.12.0

# Recreate virtual environment
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Restart simulator
python -m ot_simulator --protocol opcua --web-ui
```

**Alternative**: Use Docker container with Python 3.12 (if available in project)

**Verification**: After downgrade, you should see successful connections in logs:
```
asyncua.server.binary_server_asyncio - INFO - New connection from ('127.0.0.1', 56023)
```

### Remote Access
To allow remote connections, change the endpoint in `ot_simulator/config.yaml`:
```yaml
opcua:
  endpoint: "opc.tcp://0.0.0.0:4840/ot-simulator/server/"  # Current (all interfaces)
  # or
  endpoint: "opc.tcp://192.168.1.100:4840/ot-simulator/server/"  # Specific IP
```

## Web UI

Access the enhanced web UI at: **http://localhost:8989**

Features:
- Real-time sensor value charts
- Natural language control ("start opcua", "show me mining sensors")
- Protocol status indicators
- Sensor browser with 347 sensors across 15 industries
- WebSocket streaming for live updates
