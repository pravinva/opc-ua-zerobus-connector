# OT Simulator Docker Containers

Three independent OT simulator instances are now running in separate Docker containers for testing purposes.

## Container Summary

All containers are running with:
- OPC UA Server
- MQTT Broker (with Mosquitto)
- Modbus TCP Server
- 347 sensors across 15 industries

## Connection Details

### Simulator 1 (ot-simulator-1)
**Network:** 172.25.0.0/24 (Gateway: 172.25.0.1)
**Container IP:** 172.25.0.10

**Host Ports:**
- OPC UA: `opc.tcp://localhost:4840/ot-simulator/server/`
- MQTT: `localhost:1883`
- Modbus TCP: `localhost:5020`

**Environment:**
- SIMULATOR_ID=1
- SIMULATOR_NAME=OT-Simulator-1

---

### Simulator 2 (ot-simulator-2)
**Network:** 172.26.0.0/24 (Gateway: 172.26.0.1)
**Container IP:** 172.26.0.10

**Host Ports:**
- OPC UA: `opc.tcp://localhost:4841/ot-simulator/server/`
- MQTT: `localhost:1884`
- Modbus TCP: `localhost:5021`

**Environment:**
- SIMULATOR_ID=2
- SIMULATOR_NAME=OT-Simulator-2

---

### Simulator 3 (ot-simulator-3)
**Network:** 172.27.0.0/24 (Gateway: 172.27.0.1)
**Container IP:** 172.27.0.10

**Host Ports:**
- OPC UA: `opc.tcp://localhost:4842/ot-simulator/server/`
- MQTT: `localhost:1885`
- Modbus TCP: `localhost:5022`

**Environment:**
- SIMULATOR_ID=3
- SIMULATOR_NAME=OT-Simulator-3

---

## Docker Management Commands

### Start All Containers
```bash
# Start containers one by one (recommended)
docker-compose -f docker-compose.simulator1.yml up -d
docker-compose -f docker-compose.simulator2.yml up -d
docker-compose -f docker-compose.simulator3.yml up -d
```

### Stop All Containers
```bash
docker-compose -f docker-compose.simulator1.yml down
docker-compose -f docker-compose.simulator2.yml down
docker-compose -f docker-compose.simulator3.yml down
```

### View Container Status
```bash
docker ps --filter "name=ot-simulator"
```

### View Logs
```bash
# View logs for specific simulator
docker logs ot-simulator-1
docker logs ot-simulator-2
docker logs ot-simulator-3

# Follow logs in real-time
docker logs -f ot-simulator-1
```

### Restart a Container
```bash
docker restart ot-simulator-1
docker restart ot-simulator-2
docker restart ot-simulator-3
```

### Execute Commands Inside Container
```bash
# Get a shell inside the container
docker exec -it ot-simulator-1 bash

# Run a Python command
docker exec ot-simulator-1 python -c "import pymodbus; print(pymodbus.__version__)"
```

### Check Container Health
```bash
docker inspect ot-simulator-1 | grep -A 10 "Health"
```

---

## Network Configuration

Each simulator runs in its own isolated bridge network to prevent conflicts:

| Network Name | Subnet | Gateway | Container |
|--------------|--------|---------|-----------|
| opc-ua-zerobus-connector_ot-sim-network | 172.25.0.0/24 | 172.25.0.1 | ot-simulator-1 (172.25.0.10) |
| opc-ua-zerobus-connector_ot-sim-network-2 | 172.26.0.0/24 | 172.26.0.1 | ot-simulator-2 (172.26.0.10) |
| opc-ua-zerobus-connector_ot-sim-network-3 | 172.27.0.0/24 | 172.27.0.1 | ot-simulator-3 (172.27.0.10) |

View networks:
```bash
docker network ls | grep "ot-sim"
```

---

## Testing Connectivity

### Test OPC UA Connection
```bash
# Simulator 1
curl -X POST http://localhost:8080/api/test/opcua \
  -H "Content-Type: application/json" \
  -d '{"endpoint": "opc.tcp://localhost:4840/ot-simulator/server/"}'

# Simulator 2
curl -X POST http://localhost:8080/api/test/opcua \
  -H "Content-Type: application/json" \
  -d '{"endpoint": "opc.tcp://localhost:4841/ot-simulator/server/"}'

# Simulator 3
curl -X POST http://localhost:8080/api/test/opcua \
  -H "Content-Type: application/json" \
  -d '{"endpoint": "opc.tcp://localhost:4842/ot-simulator/server/"}'
```

### Test MQTT Connection
```bash
# Subscribe to Simulator 1
mosquitto_sub -h localhost -p 1883 -t "ot/+/+/#" -v

# Subscribe to Simulator 2
mosquitto_sub -h localhost -p 1884 -t "ot/+/+/#" -v

# Subscribe to Simulator 3
mosquitto_sub -h localhost -p 1885 -t "ot/+/+/#" -v
```

### Test Modbus Connection
Using Python:
```python
from pymodbus.client import ModbusTcpClient

# Test Simulator 1
client1 = ModbusTcpClient('localhost', port=5020)
client1.connect()
result = client1.read_holding_registers(0, 10, slave=1)
print(f"Simulator 1: {result.registers}")
client1.close()

# Test Simulator 2
client2 = ModbusTcpClient('localhost', port=5021)
client2.connect()
result = client2.read_holding_registers(0, 10, slave=1)
print(f"Simulator 2: {result.registers}")
client2.close()

# Test Simulator 3
client3 = ModbusTcpClient('localhost', port=5022)
client3.connect()
result = client3.read_holding_registers(0, 10, slave=1)
print(f"Simulator 3: {result.registers}")
client3.close()
```

---

## Troubleshooting

### Container Won't Start
```bash
# Check logs for errors
docker logs ot-simulator-1

# Check if ports are already in use
lsof -i :4840
lsof -i :1883
lsof -i :5020
```

### Port Conflicts
If ports are already in use, you can either:
1. Stop the conflicting service
2. Modify the Docker Compose files to use different host ports

### Network Issues
```bash
# Inspect network details
docker network inspect opc-ua-zerobus-connector_ot-sim-network

# Check if container is connected to network
docker inspect ot-simulator-1 | grep -A 20 "Networks"
```

### Performance Issues
```bash
# Check container resource usage
docker stats ot-simulator-1 ot-simulator-2 ot-simulator-3
```

---

## Files Created

1. **Dockerfile.simulator** - Docker image definition for OT simulator
2. **docker-compose.simulator1.yml** - Docker Compose file for Simulator 1
3. **docker-compose.simulator2.yml** - Docker Compose file for Simulator 2
4. **docker-compose.simulator3.yml** - Docker Compose file for Simulator 3

---

## Sensor Data

Each simulator contains 347 sensors across 15 industries:
- mining (17 sensors)
- utilities (18 sensors)
- manufacturing (19 sensors)
- oil_gas (26 sensors)
- aerospace (25 sensors)
- space (20 sensors)
- water_wastewater (22 sensors)
- electric_power (24 sensors)
- automotive (28 sensors)
- chemical (26 sensors)
- food_beverage (25 sensors)
- pharmaceutical (30 sensors)
- data_center (22 sensors)
- smart_building (25 sensors)
- agriculture (20 sensors)

All sensors update at 2.0 Hz and include realistic industrial data patterns with fault injection capabilities.
