# OPC-UA PLC Integration

This document explains how the OPC-UA simulator integrates with the PLC simulation layer to provide realistic hierarchical node structures matching real-world PLC deployments.

## Overview

The OPC-UA simulator now supports **two node structure modes**:

1. **Direct Mode** (default): Flat industry/sensor hierarchy
2. **PLC Mode**: Hierarchical PLC-based structure with diagnostics

## Node Structure Modes

### Direct Mode (No PLCs)

When PLC simulation is disabled or not available, the OPC-UA server creates a simple flat structure:

```
Objects/
  IndustrialSensors/
    Mining/
      crusher_1_motor_power
      crusher_1_vibration
    Utilities/
      pump_1_flow_rate
      ...
```

**Use Case**: Quick testing, simple data access, no need for PLC realism

### PLC Mode (Realistic Industrial Structure)

When PLC simulation is enabled, the OPC-UA server creates a hierarchical structure matching how real PLCs organize data:

```
Objects/
  PLCs/
    PLC_MINING (Rockwell ControlLogix 5580)/
      Diagnostics/
        Vendor: "rockwell"
        Model: "ControlLogix 5580"
        RunMode: "RUN"
        ScanCycleMs: 50
        Rack: 0
        Slot: 3
        TotalScans: 12458 (updated in real-time)
      Inputs/
        Mining/
          crusher_1_motor_power (with PLCName, PLCModel properties)
          crusher_1_vibration
      ForcedValues/
        Count: 0 (updated when values are forced)

    PLC_UTILITIES_POWER (ABB AC800M)/
      Diagnostics/
        ...
      Inputs/
        Utilities/
          pump_1_flow_rate
        Electric Power/
          grid_frequency
      ForcedValues/
        ...
```

**Use Case**: Realistic simulation, testing SCADA/HMI integration, PLC diagnostics, operator training

## How It Works

### 1. Mode Detection

The OPC-UA simulator checks for PLC manager availability during initialization:

```python
has_plc_manager = (
    self.simulator_manager
    and hasattr(self.simulator_manager, 'plc_manager')
    and self.simulator_manager.plc_manager
    and self.simulator_manager.plc_manager.enabled
)
```

### 2. Node Creation

Based on mode:
- **Direct Mode**: Calls `_create_direct_sensor_nodes()` - creates flat industry folders
- **PLC Mode**: Calls `_create_plc_based_nodes()` - creates PLC hierarchy with diagnostics

### 3. Real-Time Updates

The OPC-UA server update loop (`_run_server_loop`) handles both modes:

```python
# Update sensor values (with PLC layer if available)
for path, simulator in self.simulators.items():
    if self.simulator_manager and hasattr(self.simulator_manager, 'get_sensor_value_with_plc'):
        result = self.simulator_manager.get_sensor_value_with_plc(path)
        new_value = result.get('value')
        # Includes PLC scan cycle, quality codes, forced values
    else:
        new_value = simulator.update()  # Direct read

# Update PLC diagnostic nodes (PLC mode only)
if plc_manager and plc_manager.enabled:
    all_diag = plc_manager.get_all_diagnostics()
    for plc_name, diag in all_diag.items():
        # Update TotalScans
        await self.nodes[f"_diag_{plc_name}_scan_count"].write_value(total_scans)
        # Update ForcedValues/Count
        await self.nodes[f"_diag_{plc_name}_forced_count"].write_value(forced_count)
```

## PLC Hierarchy Features

### Diagnostics Folder

Each PLC exposes real-time diagnostics:

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| Vendor | String | PLC vendor | "rockwell" |
| Model | String | PLC model | "ControlLogix 5580" |
| RunMode | String | Current run mode | "RUN", "STOP", "FAULT" |
| ScanCycleMs | Int32 | Configured scan cycle | 50 |
| Rack | Int32 | Hardware rack position | 0 |
| Slot | Int32 | Hardware slot position | 3 |
| TotalScans | Int64 | Total scan count (live) | 12458 |

### Inputs Folder

Organized by industry, each sensor includes:

**Standard Properties** (all sensors):
- Unit: "kW", "Hz", "°C", etc.
- SensorType: "power", "flow", "temperature", etc.
- MinValue: Minimum sensor range
- MaxValue: Maximum sensor range

**PLC-Specific Properties** (PLC mode only):
- PLCName: "PLC_MINING"
- PLCModel: "ControlLogix 5580"

### ForcedValues Folder

Tracks operator overrides:
- Count: Number of currently forced values

## Vendor-to-Industry Mapping

The simulator assigns specific PLC vendors to industries based on real-world common usage:

| PLC | Vendor | Industries | Rationale |
|-----|--------|------------|-----------|
| PLC_MINING | Rockwell | Mining | North America standard for mining |
| PLC_UTILITIES_POWER | ABB | Utilities, Electric Power | Process control specialist |
| PLC_MANUFACTURING | Mitsubishi | Manufacturing, Automotive | Motion control excellence, Asia dominant |
| PLC_OIL_GAS | Schneider | Oil & Gas, Chemical | Infrastructure focus, Modicon legacy |
| PLC_FOOD_PHARMA | Omron | Food/Beverage, Pharma | Packaging specialist, hygiene standards |
| PLC_BUILDINGS | Schneider | Smart Building, Data Center | BMS standard (Modicon M340) |
| PLC_WATER_AGRICULTURE | Rockwell | Water, Agriculture | Outdoor-rated CompactLogix |
| PLC_RENEWABLE_ENERGY | Siemens | Renewable Energy | High-performance S7-1500 |

## Configuration

### Enabling PLC Mode

Edit `ot_simulator/plc_config.yaml`:

```yaml
global_plc_settings:
  enable_plc_simulation: true  # Set to false to disable PLC mode
  simulate_scan_delays: true
  simulate_quality_issues: true
  simulate_comm_failures: true
  allow_forcing: true

plcs:
  PLC_MINING:
    vendor: rockwell
    model: ControlLogix 5580
    industries:
      - mining
    enabled: true  # Set to false to disable this specific PLC
```

### Current Limitation

**Important**: The OPC-UA simulator must be started AFTER the PLC manager is initialized to use PLC mode. Currently:

- When starting with `--web-ui`, PLC manager initializes correctly
- However, OPC-UA nodes are created BEFORE PLC initialization (during protocol startup)
- Result: OPC-UA server always uses Direct Mode, even with PLCs enabled

**Workaround for now**: PLCs are working correctly for:
- WebSocket (web UI charts)
- MQTT
- Modbus
- Direct API calls

Only OPC-UA node structure is not yet using the PLC hierarchy.

## Future Enhancement

To enable PLC-based OPC-UA nodes, the startup sequence needs adjustment:

1. Start protocol simulators WITHOUT creating OPC-UA nodes
2. Initialize PLC manager
3. Initialize OPC-UA nodes (will detect PLC manager and use PLC mode)
4. Start OPC-UA server

This will be addressed in a future update to complete Step 3 of the PLC implementation plan.

## Testing

### Direct Mode
```bash
python -m ot_simulator --protocol opcua
# Browse to Objects/IndustrialSensors/
```

### PLC Mode (when fully implemented)
```bash
python -m ot_simulator --protocol opcua --web-ui
# Browse to Objects/PLCs/PLC_MINING (Rockwell ControlLogix 5580)/
# Check Diagnostics/TotalScans - should increment in real-time
# Check Inputs/Mining/crusher_1_motor_power
# Verify PLCName and PLCModel properties exist
```

## References

- **PLC Architecture**: `PLC_ARCHITECTURE.md` - Complete 4-layer architecture explanation
- **PLC Specifications**: `PLC_SPECIFICATIONS_RESEARCH.md` - Research-backed PLC specs
- **PLC Models**: `plc_models.py` - 14 PLC models with realistic behavior
- **PLC Configuration**: `plc_config.yaml` - Simple industry-to-PLC mapping
- **PLC Manager**: `plc_manager.py` - PLC instance management
- **OPC-UA Simulator**: `opcua_simulator.py` - PLC-aware node creation (lines 89-184)

## Implementation Status

- ✅ PLC models with realistic specifications (6 vendors, 14 models)
- ✅ PLC configuration system (YAML-based)
- ✅ PLC manager for multiple PLC instances
- ✅ SimulatorManager integration (PLC-aware methods)
- ✅ OPC-UA hierarchical node structure code (`_create_plc_based_nodes`)
- ✅ Real-time diagnostic updates
- ⚠️ Startup sequence needs adjustment to enable PLC mode
- ⏳ MQTT PLC-based topics (future)
- ⏳ Modbus PLC-based registers (future)
- ⏳ Web UI PLC diagnostics panel (future)

---

**Document Version**: 1.0
**Last Updated**: 2026-01-12
**Author**: Claude Code (Step 3: PLC-specific OPC-UA node structures)
