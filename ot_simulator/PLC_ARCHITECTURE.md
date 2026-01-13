# PLC Simulation Architecture

This document explains how PLC simulation works in the OT simulator and how it relates to sensors and protocols.

## Architecture Overview

The OT simulator has a **4-layer architecture** that separates concerns:

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: Protocol Exposure (Optional - Start/Stop Control) │
├─────────────────────────────────────────────────────────────┤
│  - OPC-UA Server (opc.tcp://0.0.0.0:4840)                  │
│  - MQTT Publisher (publishes to broker)                    │
│  - Modbus TCP/RTU Server                                   │
│  - WebSocket Server (for web UI charts)                    │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ Layer 3: PLC Layer (Optional - Configurable)               │
├─────────────────────────────────────────────────────────────┤
│  - PLC instances (Siemens, Rockwell, Schneider, etc.)     │
│  - Scan cycle delays (20-200ms)                            │
│  - Quality codes (Good/Uncertain/Bad)                       │
│  - Forced values (operator overrides)                       │
│  - Diagnostics (scan counts, errors, etc.)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ Layer 2: Unified Sensor Access (SimulatorManager)          │
├─────────────────────────────────────────────────────────────┤
│  - get_sensor_value(path) - Direct sensor access           │
│  - get_sensor_value_with_plc(path) - PLC-filtered access   │
│  - inject_fault(path, duration) - Fault injection          │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ Layer 1: Data Generation (Always Running)                  │
├─────────────────────────────────────────────────────────────┤
│  - 379 SensorSimulator instances                            │
│  - 16 industries (mining, utilities, manufacturing, etc.)   │
│  - Continuous updates (independent of protocols)            │
│  - Realistic behavior models (cyclic, drift, noise)         │
└─────────────────────────────────────────────────────────────┘
```

## Key Architectural Principles

### 1. PLCs Are Protocol-Independent

**Important**: PLCs work with **ALL protocols** (OPC-UA, MQTT, Modbus), not just OPC-UA.

This is realistic because in a real industrial plant:
- Sensors are wired to PLCs (not directly to network)
- PLCs process sensor signals (A/D conversion, scaling, quality checks)
- Multiple protocols can connect to the **same PLC** to read the **same data**

**Example in the simulator**:
```yaml
# plc_config.yaml
PLC_MINING:
  vendor: rockwell
  model: ControlLogix 5580
  industries:
    - mining
  scan_cycle_ms: 50
```

When this PLC is configured:
- ALL mining sensors are processed through this PLC
- OPC-UA clients reading `mining/crusher_1_motor_power` get PLC-filtered data
- MQTT subscribers to `mining/crusher_1_motor_power` get the **same** PLC-filtered data
- Modbus masters reading the crusher power register get the **same** PLC-filtered data

### 2. Data Flow Examples

#### Example 1: Reading a Sensor with PLC Enabled

```python
# User reads mining/crusher_1_motor_power via OPC-UA

Layer 4 (OPC-UA): Client requests node value
    ↓
Layer 3 (PLC): PLC_MINING (Rockwell ControlLogix)
    - Check scan buffer (updated every 50ms)
    - Check for forced values (none)
    - Determine quality code (Good)
    - Return: {value: 1250.5, quality: "Good", scan_count: 12458}
    ↓
Layer 2 (SimulatorManager): Route request to PLC
    ↓
Layer 1 (SensorSimulator): Generate current value
    - Current value: 1250.5 kW
    - No active fault
```

#### Example 2: Same Sensor Read via MQTT

```python
# User subscribes to mining/crusher_1_motor_power via MQTT

Layer 4 (MQTT): Publish sensor update
    ↓
Layer 3 (PLC): SAME PLC_MINING instance
    - SAME scan buffer (updated every 50ms)
    - SAME quality determination logic
    - Return: {value: 1250.5, quality: "Good", scan_count: 12458}
    ↓
Layer 2 (SimulatorManager): SAME routing logic
    ↓
Layer 1 (SensorSimulator): SAME sensor instance
    - SAME current value: 1250.5 kW
```

**Result**: Both OPC-UA and MQTT see identical data because they go through the same PLC.

#### Example 3: Reading Without PLC (Direct Mode)

If PLCs are disabled in config:
```yaml
global_plc_settings:
  enable_plc_simulation: false
```

Then:
```python
Layer 4 (Any Protocol): Request sensor value
    ↓
Layer 3 (PLC): BYPASSED
    ↓
Layer 2 (SimulatorManager): Direct sensor access
    ↓
Layer 1 (SensorSimulator): Return raw value
    - Value: 1250.5 kW (no scan delay, always "Good" quality)
```

### 3. Fault Injection Propagates to All

When a fault is injected:
```python
# Operator injects fault: mining/crusher_1_motor_power = 0 for 30 seconds

Layer 1 (SensorSimulator): Fault stored
    ↓
Layer 2 (SimulatorManager): All readers see fault
    ↓
Layer 3 (PLC): PLC reads faulty value, may add quality code
    ↓
Layer 4 (All Protocols): Everyone sees the fault
    - OPC-UA clients see value=0, quality="Bad_SensorFailure"
    - MQTT subscribers see value=0, quality="Bad_SensorFailure"
    - Modbus masters see value=0, quality code 0x808F (bad sensor)
    - Web UI charts see value=0 with red indicator
```

### 4. Charts Work Without Starting Protocols

**Important Insight**: The web UI charts work **WITHOUT** starting any protocols.

```python
# User opens web UI and adds chart for mining/crusher_1_motor_power
# (No protocols started yet - user didn't click "Start")

Layer 4 (WebSocket): WebSocket connection established
    ↓
Layer 3 (PLC): If enabled, route through PLC
    ↓
Layer 2 (SimulatorManager): get_sensor_value_with_plc()
    ↓
Layer 1 (SensorSimulator): Return current value
    ↓
WebSocket: Send to browser every 500ms
    ↓
Chart.js: Render data point
```

**Why this works**:
- Sensors (Layer 1) start immediately at startup
- WebSocket server connects directly to Layer 2 (SimulatorManager)
- Protocol servers (Layer 4) are **optional network endpoints**
- Charts don't need protocols - they use WebSocket directly

### 5. Protocol Start/Stop Only Controls Network Endpoints

When you click "Start OPC-UA":
- Creates OPC-UA server on `opc.tcp://0.0.0.0:4840`
- External clients can now connect
- Sensors keep running (they never stopped)
- PLC keeps processing (if enabled)

When you click "Stop OPC-UA":
- Closes OPC-UA server endpoint
- External clients can no longer connect
- Sensors keep running
- PLC keeps processing
- **Charts still work** (they use WebSocket, not OPC-UA)

## PLC Configuration

### Vendor-to-Industry Mapping

The simulator includes realistic vendor-to-industry assignments:

| PLC | Vendor | Model | Industries | Rationale |
|-----|--------|-------|------------|-----------|
| PLC_RENEWABLE_ENERGY | Siemens | S7-1500 | Renewable Energy | High-performance, fast scan (50ms) |
| PLC_MINING | Rockwell | ControlLogix 5580 | Mining | North America standard, rugged |
| PLC_UTILITIES_POWER | ABB | AC800M | Utilities, Electric Power | Process control specialist |
| PLC_MANUFACTURING | Mitsubishi | MELSEC iQ-R | Manufacturing, Automotive | Motion control excellence |
| PLC_OIL_GAS | Schneider | Modicon M580 | Oil & Gas, Chemical | Infrastructure focus, Ethernet |
| PLC_FOOD_PHARMA | Omron | Sysmac NJ | Food/Beverage, Pharma | Packaging, hygiene standards |
| PLC_BUILDINGS | Schneider | Modicon M340 | Smart Building, Data Center | BMS standard |
| PLC_WATER_AGRICULTURE | Rockwell | CompactLogix 5380 | Water, Agriculture | Compact, outdoor-rated |

### PLC Features Simulated

1. **Scan Cycle Delays**
   - Entry PLCs (MicroLogix, S7-300): 150-200ms
   - Standard PLCs (S7-1200, CompactLogix, M340): 75-150ms
   - High-Performance (S7-1500, ControlLogix 5580, M580): 50-100ms
   - Motion-Optimized (iQ-R, Sysmac NJ, AC800M): 20-75ms

2. **OPC-UA Quality Codes**
   - `Good` (0x00000000): Normal operation
   - `Good_LocalOverride` (0x00960000): Forced value active
   - `Uncertain` (0x40000000): Sensor questionable
   - `Uncertain_SensorNotAccurate` (0x40940000): Sensor degraded
   - `Bad` (0x80000000): Communication failure
   - `Bad_NotConnected` (0x800A0000): I/O module offline
   - `Bad_DeviceFailure` (0x800E0000): Hardware fault
   - `Bad_SensorFailure` (0x808F0000): Sensor fault
   - `Bad_OutOfService` (0x808D0000): PLC in STOP mode

3. **Value Forcing** (Operator Override)
   - Simulates PLC operator forcing values
   - Used for testing, commissioning, troubleshooting
   - Sets quality to `Good_LocalOverride`
   - Supported by most modern PLCs (except entry-level like MicroLogix)

4. **Diagnostics**
   - Total scans
   - Scan overruns (when scan takes longer than cycle time)
   - Communication errors
   - Sensor errors
   - Number of forced values

5. **Run Modes**
   - `RUN`: Normal operation
   - `STOP`: Program stopped, outputs `Bad_OutOfService`
   - `PROGRAM`: Programming mode
   - `FAULT`: Fault state, outputs `Bad_DeviceFailure`
   - `STARTUP`: Initializing

## Realistic Behavior

### Why Scan Cycle Delays Matter

In real PLCs:
- Sensors are NOT read on-demand
- PLC scans inputs at the start of each cycle
- Values are buffered in memory
- All program logic uses the buffered values
- Outputs are updated at the end of the cycle

This means:
- A sensor value changing mid-cycle is **not seen** until next cycle
- Fast changes (< scan cycle time) may be **missed**
- This is why high-speed applications need fast PLCs (20-50ms scan)

### Simulation Accuracy

Our scan cycle simulation is **conservative** (higher than spec sheet minimums) because:
1. **I/O Overhead**: Reading/writing hundreds of I/O points adds 5-50ms
2. **Communication Tasks**: OPC-UA, EtherNet/IP, Profinet add 10-100ms
3. **Program Complexity**: Real industrial programs with thousands of rungs
4. **HMI Updates**: Screen refresh and data logging
5. **Motion Control**: Coordinated motion adds overhead
6. **Safety Logic**: Additional certified logic paths
7. **Diagnostics**: Continuous health monitoring

**Example**: Mitsubishi iQ-R spec sheet says 0.14ms minimum scan, but we simulate 50-75ms because:
- 0.14ms is for an **empty program** with no I/O
- Real applications with I/O, communications, and logic run 20-100ms
- Conservative values ensure customers see realistic behavior

## Configuration

### Enabling/Disabling PLCs

Edit `ot_simulator/plc_config.yaml`:

```yaml
global_plc_settings:
  enable_plc_simulation: true  # Set to false to bypass PLCs
  simulate_scan_delays: true
  simulate_quality_issues: true
  simulate_comm_failures: true
  allow_forcing: true
```

### Adding a New PLC

```yaml
plcs:
  MY_CUSTOM_PLC:
    vendor: siemens
    model: S7-1500
    industries:
      - my_custom_industry
    rack: 0
    slot: 2
    enabled: true
```

### Disabling a Specific PLC

```yaml
plcs:
  PLC_AEROSPACE:
    vendor: siemens
    model: S7-1200
    industries:
      - aerospace
      - space
    enabled: false  # This PLC won't be loaded
```

## API Usage

### Reading Sensor Values

```python
# Without PLC (direct from sensor)
value = simulator_manager.get_sensor_value("mining/crusher_1_motor_power")
# Returns: 1250.5 (just the float value)

# With PLC (realistic PLC behavior)
result = simulator_manager.get_sensor_value_with_plc("mining/crusher_1_motor_power")
# Returns: {
#   "value": 1250.5,
#   "quality": "Good",
#   "timestamp": 1736683491.797,
#   "plc_name": "PLC_MINING",
#   "plc_model": "ControlLogix 5580",
#   "plc_mode": "RUN",
#   "forced": False,
#   "rack": 0,
#   "slot": 3,
#   "scan_count": 12458
# }
```

### Forcing Values

```python
# Force a value (operator override)
success = simulator_manager.force_sensor_value("mining/crusher_1_motor_power", 0.0)

# Unforce (return to normal)
success = simulator_manager.unforce_sensor_value("mining/crusher_1_motor_power")
```

### Getting PLC Information

```python
# Get all configured PLCs
plcs = simulator_manager.get_all_plcs()
# Returns: {"PLC_MINING": {...}, "PLC_UTILITIES_POWER": {...}, ...}

# Get diagnostics for specific PLC
diag = simulator_manager.get_plc_diagnostics("PLC_MINING")
# Returns: {
#   "plc_name": "PLC_MINING",
#   "plc_model": "ControlLogix 5580",
#   "vendor": "rockwell",
#   "run_mode": "RUN",
#   "scan_cycle_ms": 50,
#   "counters": {
#     "total_scans": 12458,
#     "scan_overruns": 0,
#     "comm_errors": 2,
#     "sensor_errors": 0,
#     "forced_values_count": 0
#   }
# }
```

## References

- **PLC Specifications Research**: `PLC_SPECIFICATIONS_RESEARCH.md` - Research-backed specifications with sources
- **Sensor Models**: `sensor_models.py` - 379 sensors across 16 industries
- **PLC Models**: `plc_models.py` - 14 PLC models from 6 vendors
- **PLC Manager**: `plc_manager.py` - PLC instance management
- **PLC Configuration**: `plc_config.yaml` - PLC-to-industry assignments

## Troubleshooting

### PLCs Not Loading

Check the logs for:
```
✓ PLC Manager initialized with 8 active PLCs
```

If you see:
```
PLC simulation disabled or config not found
```

Verify:
1. `plc_config.yaml` exists in `ot_simulator/` directory
2. `enable_plc_simulation: true` in global settings
3. At least one PLC has `enabled: true`

### Scan Cycle Not Working

Check configuration:
```yaml
global_plc_settings:
  simulate_scan_delays: true  # Must be true
```

### Quality Codes Always "Good"

Check configuration:
```yaml
global_plc_settings:
  simulate_quality_issues: true  # For random quality issues
  quality_issue_probability: 0.0005  # 0.05% per read
  simulate_comm_failures: true  # For communication failures
  comm_failure_probability: 0.0001  # 0.01% per read
```

Note: Quality issues are **rare by design** (0.01-0.05% chance) to simulate realistic PLC behavior.
