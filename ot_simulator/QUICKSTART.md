# OT Simulator - Quick Start

## Install & Run (30 seconds)

```bash
# 1. Install
pip install -r requirements.txt

# 2. Run all protocols
python -m ot_simulator

# 3. Access UI
open http://localhost:8989
```

## Common Commands

```bash
# Start specific protocols
python -m ot_simulator --protocol opcua
python -m ot_simulator --protocol mqtt
python -m ot_simulator --protocol modbus

# Run all with web UI
python -m ot_simulator --web-ui

# Custom config
python -m ot_simulator --config custom.yaml

# List all sensors
python -m ot_simulator --list-sensors

# Debug mode
python -m ot_simulator --log-level DEBUG
```

## Default Endpoints

| Protocol | Endpoint | Test Tool |
|----------|----------|-----------|
| OPC-UA | `opc.tcp://localhost:4840` | UaExpert, Prosys |
| MQTT | `mqtt://localhost:1883` | mosquitto_sub |
| Modbus | `modbus://localhost:5020` | modpoll |
| Web UI | `http://localhost:8989` | Browser |
| Metrics | `http://localhost:9091/metrics` | Prometheus |

## Test Commands

### OPC-UA (UaExpert)
1. Connect to `opc.tcp://localhost:4840`
2. Browse: `Industries` → `mining` → `crusher_1_motor_power`
3. Subscribe and watch live updates

### MQTT (mosquitto_sub)
```bash
# Subscribe to all sensors
mosquitto_sub -h localhost -t "sensors/#" -v

# Subscribe to mining only
mosquitto_sub -h localhost -t "sensors/mining/#" -v
```

### Modbus (modpoll)
```bash
# Read mining sensors (addr 0-15)
modpoll -m tcp -a 1 -r 0 -c 16 localhost 5020

# Read utilities sensors (addr 1000-1016)
modpoll -m tcp -a 1 -r 1000 -c 17 localhost 5020
```

## Connect to IoT Connector

Add to `config.yaml`:

```yaml
sources:
  - name: "sim-opcua"
    endpoint: "opc.tcp://localhost:4840"
    protocol_type: "opcua"
    variable_limit: 20

  - name: "sim-mqtt"
    endpoint: "mqtt://localhost:1883"
    protocol_type: "mqtt"
    mqtt:
      topics: ["sensors/mining/#"]

  - name: "sim-modbus"
    endpoint: "modbus://localhost:5020"
    protocol_type: "modbus"
    modbus:
      slave_id: 1
      registers:
        - address: 0
          count: 16
```

Then run connector:
```bash
python -m opcua2uc --config config.yaml
```

## Inject Faults (Testing)

```bash
curl -X POST http://localhost:8989/api/fault/inject \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "opcua",
    "sensor_path": "mining/crusher_1_motor_power",
    "duration": 30
  }'
```

## What You Get

- **78 Sensors** across 4 industries
- **3 Protocols** (OPC-UA, MQTT, Modbus)
- **Realistic Data** with noise, drift, cycles
- **Web UI** for monitoring
- **Fault Injection** for testing

## Sensors by Industry

- **Mining** (16): Crushers, conveyors, pumps
- **Utilities** (17): Grid, transformers, batteries
- **Manufacturing** (18): Robots, presses, welders
- **Oil & Gas** (27): Pipelines, compressors, tanks

## Troubleshooting

**Port in use?**
```bash
# Check what's using port
lsof -i :8989

# Change port in config
python -m ot_simulator --web-port 9000
```

**Can't connect?**
```bash
# Check simulator is running
ps aux | grep ot_simulator

# Check endpoint is listening
lsof -i :4840   # OPC-UA
lsof -i :1883   # MQTT
lsof -i :5020   # Modbus
```

## Documentation

- **Full Guide:** `ot_simulator/README.md` (900+ lines)
- **Port Config:** `PORTS.md`
- **Protocols:** `PROTOCOLS.md`
- **Complete Summary:** `OT_SIMULATOR_COMPLETE.md`

## Docker (Optional)

```bash
docker run -d \
  --name ot-simulator \
  -p 8989:8989 \
  -p 4840:4840 \
  -p 1883:1883 \
  -p 5020:5020 \
  ot-simulator
```

---

**Need help?** See full documentation in `ot_simulator/README.md`
