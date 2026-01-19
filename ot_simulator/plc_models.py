"""PLC simulation layer - adds PLC-specific behavior to sensor data.

Simulates realistic PLC behavior from major vendors:
- Siemens S7 (Germany) - Market leader
- Rockwell/Allen-Bradley (USA) - North America dominant
- Schneider Modicon (France) - Infrastructure/energy
- ABB AC500 (Switzerland) - Power/robotics
- Mitsubishi MELSEC (Japan) - Asia/discrete manufacturing
- Omron Sysmac (Japan) - Asia/packaging
"""

from __future__ import annotations

import random
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("ot_simulator.plc")


class PLCVendor(str, Enum):
    """PLC vendor types."""

    SIEMENS = "siemens"
    ROCKWELL = "rockwell"  # Allen-Bradley
    SCHNEIDER = "schneider"
    ABB = "abb"
    MITSUBISHI = "mitsubishi"
    OMRON = "omron"


class PLCQualityCode(str, Enum):
    """OPC-UA quality codes used by PLCs.

    Based on OPC-UA StatusCode specification.
    """

    GOOD = "Good"  # 0x00000000
    GOOD_LOCAL_OVERRIDE = "Good_LocalOverride"  # 0x00960000 (Forced value)
    UNCERTAIN = "Uncertain"  # 0x40000000
    UNCERTAIN_SENSOR_NOT_ACCURATE = "Uncertain_SensorNotAccurate"  # 0x40940000
    BAD = "Bad"  # 0x80000000
    BAD_NOT_CONNECTED = "Bad_NotConnected"  # 0x800A0000
    BAD_DEVICE_FAILURE = "Bad_DeviceFailure"  # 0x800E0000
    BAD_SENSOR_FAILURE = "Bad_SensorFailure"  # 0x808F0000
    BAD_OUT_OF_SERVICE = "Bad_OutOfService"  # 0x808D0000
    BAD_COMM_FAILURE = "Bad_CommunicationFailure"  # 0x80050000


class PLCRunMode(str, Enum):
    """PLC operational modes."""

    RUN = "RUN"  # Normal operation
    STOP = "STOP"  # Program stopped
    PROGRAM = "PROGRAM"  # Programming mode
    FAULT = "FAULT"  # Fault state
    STARTUP = "STARTUP"  # Initializing


@dataclass
class PLCConfig:
    """Configuration for a PLC."""

    vendor: PLCVendor
    model: str  # e.g., "S7-1500", "ControlLogix 5580"
    name: str  # e.g., "PLC_WIND_TURBINE_1"

    # Hardware configuration
    rack: int = 0
    slot: int = 2

    # Timing configuration
    scan_cycle_ms: int = 100  # PLC scan cycle in milliseconds (typical: 10-100ms)

    # Simulation behavior
    simulate_scan_delay: bool = True  # Enforce scan cycle timing
    simulate_quality_issues: bool = True  # Random quality degradation
    quality_issue_probability: float = 0.0005  # 0.05% chance per read (rare but realistic)
    simulate_comm_failures: bool = True  # Occasional comm failures
    comm_failure_probability: float = 0.0001  # 0.01% chance

    # PLC-specific features
    supports_forcing: bool = True  # Allow operator to force values
    supports_diagnostics: bool = True  # Expose diagnostic counters

    # Industry assignment (which sensors this PLC controls)
    assigned_industries: list[str] = field(default_factory=list)


# Vendor-specific PLC models with realistic specifications
PLC_MODELS = {
    PLCVendor.SIEMENS: {
        "S7-1500": {
            "scan_cycle_ms": 50,  # Very fast
            "description": "High-performance PLC, automotive/manufacturing",
            "supports_forcing": True,
            "supports_diagnostics": True,
        },
        "S7-1200": {
            "scan_cycle_ms": 100,  # Standard
            "description": "Compact PLC, general automation",
            "supports_forcing": True,
            "supports_diagnostics": True,
        },
        "S7-300": {
            "scan_cycle_ms": 150,  # Older, slower
            "description": "Legacy PLC, still widely deployed",
            "supports_forcing": True,
            "supports_diagnostics": False,  # Limited diagnostics
        },
    },
    PLCVendor.ROCKWELL: {
        "ControlLogix 5580": {
            "scan_cycle_ms": 50,  # High performance
            "description": "High-end PLC, process/hybrid industries",
            "supports_forcing": True,
            "supports_diagnostics": True,
        },
        "CompactLogix 5380": {
            "scan_cycle_ms": 75,  # Mid-range
            "description": "Compact PLC, machine automation",
            "supports_forcing": True,
            "supports_diagnostics": True,
        },
        "MicroLogix 1400": {
            "scan_cycle_ms": 200,  # Entry-level, slower
            "description": "Entry-level PLC, small machines",
            "supports_forcing": False,  # Limited features
            "supports_diagnostics": False,
        },
    },
    PLCVendor.SCHNEIDER: {
        "Modicon M580": {
            "scan_cycle_ms": 100,  # Standard
            "description": "High-performance PAC, infrastructure",
            "supports_forcing": True,
            "supports_diagnostics": True,
        },
        "Modicon M340": {
            "scan_cycle_ms": 150,  # Mid-range
            "description": "Modular PLC, building automation",
            "supports_forcing": True,
            "supports_diagnostics": True,
        },
    },
    PLCVendor.ABB: {
        "AC500": {
            "scan_cycle_ms": 100,  # Standard
            "description": "Modular PLC, power/robotics",
            "supports_forcing": True,
            "supports_diagnostics": True,
        },
        "AC800M": {
            "scan_cycle_ms": 50,  # High performance for critical control
            "description": "Process controller, power generation",
            "supports_forcing": True,
            "supports_diagnostics": True,
        },
    },
    PLCVendor.MITSUBISHI: {
        "MELSEC iQ-R": {
            "scan_cycle_ms": 75,  # Fast
            "description": "High-speed motion control, manufacturing",
            "supports_forcing": True,
            "supports_diagnostics": True,
        },
        "MELSEC Q": {
            "scan_cycle_ms": 100,  # Standard
            "description": "Modular PLC, discrete manufacturing",
            "supports_forcing": True,
            "supports_diagnostics": True,
        },
    },
    PLCVendor.OMRON: {
        "Sysmac NJ": {
            "scan_cycle_ms": 50,  # Very fast for motion
            "description": "Machine automation controller, packaging",
            "supports_forcing": True,
            "supports_diagnostics": True,
        },
        "Sysmac CJ2": {
            "scan_cycle_ms": 100,  # Standard
            "description": "Compact PLC, machine control",
            "supports_forcing": True,
            "supports_diagnostics": True,
        },
    },
}


class PLCSimulator:
    """Simulates PLC behavior wrapping sensor data.

    Adds realistic PLC characteristics:
    - Scan cycle delays (not real-time)
    - Quality codes (OPC-UA StatusCodes)
    - Forced values (operator overrides)
    - Communication failures
    - PLC run mode (RUN/STOP/FAULT)
    """

    def __init__(self, config: PLCConfig, sensor_manager):
        """Initialize PLC simulator.

        Args:
            config: PLC configuration
            sensor_manager: Reference to SimulatorManager for sensor access
        """
        self.config = config
        self.sensor_manager = sensor_manager
        self.run_mode = PLCRunMode.RUN

        # Scan cycle management
        self.last_scan_time = time.time()
        self.scan_buffer: dict[str, float] = {}  # Cache from last scan cycle
        self.scan_count = 0

        # PLC features
        self.forced_values: dict[str, float] = {}  # Operator forced values
        self.quality_overrides: dict[str, PLCQualityCode] = {}  # Manual quality overrides

        # Diagnostics
        self.diagnostic_counters = {
            "total_scans": 0,
            "scan_overruns": 0,  # Scan took longer than cycle time
            "comm_errors": 0,
            "sensor_errors": 0,
            "forced_values_count": 0,
        }

        logger.info(
            f"Initialized {config.vendor.value} PLC: {config.model} "
            f"(scan cycle: {config.scan_cycle_ms}ms, industries: {config.assigned_industries})"
        )

    def read_input(self, sensor_path: str) -> dict[str, Any]:
        """Read sensor value through PLC input module.

        Simulates PLC I/O scan with realistic timing and quality codes.

        Args:
            sensor_path: Sensor path (e.g., "mining/crusher_1_motor_power")

        Returns:
            Dictionary with value, quality, timestamp, PLC metadata
        """
        current_time = time.time()

        # Check PLC run mode
        if self.run_mode == PLCRunMode.STOP:
            return {
                "value": None,
                "quality": PLCQualityCode.BAD_OUT_OF_SERVICE,
                "timestamp": current_time,
                "plc_name": self.config.name,
                "plc_model": self.config.model,
                "plc_mode": self.run_mode.value,
                "forced": False,
            }

        if self.run_mode == PLCRunMode.FAULT:
            return {
                "value": None,
                "quality": PLCQualityCode.BAD_DEVICE_FAILURE,
                "timestamp": current_time,
                "plc_name": self.config.name,
                "plc_model": self.config.model,
                "plc_mode": self.run_mode.value,
                "forced": False,
            }

        # Check if forced value exists (operator forced the value)
        if sensor_path in self.forced_values:
            return {
                "value": self.forced_values[sensor_path],
                "quality": PLCQualityCode.GOOD_LOCAL_OVERRIDE,
                "timestamp": current_time,
                "plc_name": self.config.name,
                "plc_model": self.config.model,
                "plc_mode": self.run_mode.value,
                "forced": True,
                "rack": self.config.rack,
                "slot": self.config.slot,
            }

        # Scan cycle simulation - only update buffer at scan intervals
        if self.config.simulate_scan_delay:
            scan_elapsed = current_time - self.last_scan_time
            if scan_elapsed >= self.config.scan_cycle_ms / 1000:
                self.last_scan_time = current_time
                self.scan_count += 1
                self.diagnostic_counters["total_scans"] += 1

                # Check for scan overrun
                if scan_elapsed > (self.config.scan_cycle_ms / 1000) * 1.5:
                    self.diagnostic_counters["scan_overruns"] += 1
                    logger.warning(
                        f"{self.config.name}: Scan overrun detected "
                        f"({scan_elapsed*1000:.1f}ms > {self.config.scan_cycle_ms}ms)"
                    )

                # Update entire scan buffer
                self._update_scan_buffer()

        # Get value from scan buffer or directly from sensor
        if sensor_path in self.scan_buffer:
            value = self.scan_buffer[sensor_path]
        else:
            value = self.sensor_manager.get_sensor_value(sensor_path)

        # Determine quality code
        quality = self._determine_quality(sensor_path, value)

        # Update diagnostics
        if quality in [PLCQualityCode.BAD_COMM_FAILURE]:
            self.diagnostic_counters["comm_errors"] += 1
        if quality in [PLCQualityCode.BAD_SENSOR_FAILURE, PLCQualityCode.BAD_DEVICE_FAILURE]:
            self.diagnostic_counters["sensor_errors"] += 1

        return {
            "value": value,
            "quality": quality,
            "timestamp": current_time,
            "plc_name": self.config.name,
            "plc_model": self.config.model,
            "plc_mode": self.run_mode.value,
            "forced": False,
            "rack": self.config.rack,
            "slot": self.config.slot,
            "scan_count": self.scan_count,
        }

    def _update_scan_buffer(self):
        """Update scan buffer with fresh sensor values (simulates PLC I/O scan)."""
        # In real PLC, this would read all inputs at once during I/O scan phase
        # For now, we'll update on-demand to avoid scanning all 379 sensors every cycle
        pass

    def _determine_quality(self, sensor_path: str, value: Optional[float]) -> PLCQualityCode:
        """Determine OPC-UA quality code based on sensor state.

        Args:
            sensor_path: Sensor path
            value: Sensor value (None if sensor failed)

        Returns:
            OPC-UA quality code
        """
        # Check for manual quality override
        if sensor_path in self.quality_overrides:
            return self.quality_overrides[sensor_path]

        # Check if value is None (sensor failure)
        if value is None:
            return PLCQualityCode.BAD_SENSOR_FAILURE

        # Simulate communication failures (very rare)
        if self.config.simulate_comm_failures:
            if random.random() < self.config.comm_failure_probability:
                return PLCQualityCode.BAD_COMM_FAILURE

        # Simulate occasional quality issues (rare but realistic)
        if self.config.simulate_quality_issues:
            if random.random() < self.config.quality_issue_probability:
                return random.choice(
                    [
                        PLCQualityCode.UNCERTAIN,
                        PLCQualityCode.UNCERTAIN_SENSOR_NOT_ACCURATE,
                    ]
                )

        return PLCQualityCode.GOOD

    def force_value(self, sensor_path: str, value: float):
        """Force a value (PLC operator feature).

        Args:
            sensor_path: Sensor to force
            value: Forced value
        """
        if not self.config.supports_forcing:
            logger.warning(f"{self.config.model} does not support forcing values")
            return

        self.forced_values[sensor_path] = value
        self.diagnostic_counters["forced_values_count"] = len(self.forced_values)
        logger.info(f"{self.config.name}: Forced {sensor_path} = {value}")

    def unforce_value(self, sensor_path: str):
        """Remove forced value.

        Args:
            sensor_path: Sensor to unforce
        """
        if sensor_path in self.forced_values:
            del self.forced_values[sensor_path]
            self.diagnostic_counters["forced_values_count"] = len(self.forced_values)
            logger.info(f"{self.config.name}: Unforced {sensor_path}")

    def set_run_mode(self, mode: PLCRunMode):
        """Set PLC run mode.

        Args:
            mode: New run mode
        """
        old_mode = self.run_mode
        self.run_mode = mode
        logger.info(f"{self.config.name}: Mode changed {old_mode.value} → {mode.value}")

    def get_diagnostics(self) -> dict[str, Any]:
        """Get PLC diagnostic information.

        Returns:
            Dictionary with diagnostic counters and status
        """
        if not self.config.supports_diagnostics:
            return {"supported": False}

        return {
            "supported": True,
            "plc_name": self.config.name,
            "plc_model": self.config.model,
            "vendor": self.config.vendor.value,
            "run_mode": self.run_mode.value,
            "scan_cycle_ms": self.config.scan_cycle_ms,
            "uptime_seconds": time.time() - self.last_scan_time,
            "counters": self.diagnostic_counters.copy(),
            "forced_values": list(self.forced_values.keys()),
        }


def create_plc_from_model(
    vendor: PLCVendor, model: str, name: str, assigned_industries: list[str], sensor_manager
) -> PLCSimulator:
    """Create a PLC simulator from vendor and model name.

    Args:
        vendor: PLC vendor
        model: Model name (must exist in PLC_MODELS)
        name: Instance name for this PLC
        assigned_industries: List of industries this PLC controls
        sensor_manager: Reference to SimulatorManager

    Returns:
        Configured PLCSimulator instance

    Raises:
        ValueError: If vendor or model is invalid
    """
    if vendor not in PLC_MODELS:
        raise ValueError(f"Unknown PLC vendor: {vendor}")

    if model not in PLC_MODELS[vendor]:
        available = ", ".join(PLC_MODELS[vendor].keys())
        raise ValueError(f"Unknown model {model} for {vendor}. Available: {available}")

    model_spec = PLC_MODELS[vendor][model]

    config = PLCConfig(
        vendor=vendor,
        model=model,
        name=name,
        scan_cycle_ms=model_spec["scan_cycle_ms"],
        supports_forcing=model_spec["supports_forcing"],
        supports_diagnostics=model_spec["supports_diagnostics"],
        assigned_industries=assigned_industries,
    )

    return PLCSimulator(config, sensor_manager)
