"""Simulator Manager - coordinates all protocol simulators and sensor access."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from ot_simulator.sensor_models import IndustryType, get_industry_sensors

logger = logging.getLogger("ot_simulator.manager")


class SimulatorManager:
    """Manages all protocol simulators and provides unified sensor access."""

    def __init__(self):
        """Initialize simulator manager."""
        self.simulators: dict[str, Any] = {}
        self.sensor_instances: dict[str, Any] = {}  # sensor_path -> Sensor instance
        self.faults: dict[str, dict] = {}  # sensor_path -> {end_time, original_value}
        self.plc_manager: Optional[Any] = None  # PLCManager instance (loaded lazily)
        self._init_sensors()

    def _init_sensors(self):
        """Initialize all sensors from all industries."""
        for industry in IndustryType:
            sensors = get_industry_sensors(industry)
            for sensor in sensors:
                sensor_path = f"{industry.value}/{sensor.config.name}"
                self.sensor_instances[sensor_path] = sensor
                logger.debug(f"Registered sensor: {sensor_path}")

        logger.info(f"Initialized {len(self.sensor_instances)} sensors across {len(IndustryType)} industries")

    def init_plc_manager(self, config_path: Optional[str] = None):
        """Initialize PLC manager (optional).

        Args:
            config_path: Path to plc_config.yaml (defaults to ot_simulator/plc_config.yaml)
        """
        try:
            from ot_simulator.plc_manager import PLCManager

            self.plc_manager = PLCManager(self, config_path)
            if self.plc_manager.load_config():
                logger.info("✓ PLC Manager initialized")
            else:
                logger.info("PLC simulation disabled or config not found")
                self.plc_manager = None
        except Exception as e:
            logger.warning(f"Failed to initialize PLC manager: {e}")
            self.plc_manager = None

    def register_simulator(self, protocol: str, simulator: Any):
        """Register a protocol simulator.

        Args:
            protocol: Protocol name (opcua, mqtt, modbus)
            simulator: Simulator instance
        """
        self.simulators[protocol] = simulator
        logger.info(f"Registered {protocol.upper()} simulator")

    async def start_simulator(self, protocol: str):
        """Start a protocol simulator.

        Args:
            protocol: Protocol name (opcua, mqtt, modbus)
        """
        if protocol not in self.simulators:
            raise ValueError(f"Unknown protocol: {protocol}")

        simulator = self.simulators[protocol]
        if hasattr(simulator, "start"):
            await simulator.start()
        logger.info(f"Started {protocol.upper()} simulator")

    async def stop_simulator(self, protocol: str):
        """Stop a protocol simulator.

        Args:
            protocol: Protocol name (opcua, mqtt, modbus)
        """
        if protocol not in self.simulators:
            raise ValueError(f"Unknown protocol: {protocol}")

        simulator = self.simulators[protocol]
        if hasattr(simulator, "stop"):
            await simulator.stop()
        logger.info(f"Stopped {protocol.upper()} simulator")

    def get_sensor_value(self, sensor_path: str) -> float | None:
        """Get current value of a sensor.

        Args:
            sensor_path: Sensor path (e.g., "mining/crusher_1_motor_power")

        Returns:
            Current sensor value or None if sensor not found
        """
        sensor = self.sensor_instances.get(sensor_path)
        if sensor is None:
            return None

        # Check if sensor has active fault
        if sensor_path in self.faults:
            fault_info = self.faults[sensor_path]
            if asyncio.get_event_loop().time() < fault_info["end_time"]:
                return fault_info.get("fault_value", 0.0)
            else:
                # Fault expired, remove it
                del self.faults[sensor_path]

        # Return normal sensor value
        return sensor.update()

    async def inject_fault(self, sensor_path: str, duration: int):
        """Inject a fault into a sensor.

        Args:
            sensor_path: Sensor path (e.g., "mining/crusher_1_motor_power")
            duration: Fault duration in seconds
        """
        if sensor_path not in self.sensor_instances:
            raise ValueError(f"Unknown sensor: {sensor_path}")

        # Calculate fault end time
        end_time = asyncio.get_event_loop().time() + duration

        # Store fault information
        self.faults[sensor_path] = {
            "end_time": end_time,
            "fault_value": 0.0,  # Set to zero or out-of-range value
            "duration": duration,
        }

        logger.info(f"Injected fault into {sensor_path} for {duration} seconds")

    def get_all_sensor_paths(self) -> list[str]:
        """Get list of all available sensor paths."""
        return list(self.sensor_instances.keys())

    def get_sensors_by_industry(self, industry: str) -> list[dict]:
        """Get all sensors for a specific industry.

        Args:
            industry: Industry name (e.g., "mining")

        Returns:
            List of sensor info dictionaries
        """
        sensors = []
        prefix = f"{industry}/"

        for path, sensor in self.sensor_instances.items():
            if path.startswith(prefix):
                sensors.append(
                    {
                        "path": path,
                        "name": sensor.config.name,
                        "min_value": sensor.config.min_value,
                        "max_value": sensor.config.max_value,
                        "unit": sensor.config.unit,
                        "type": sensor.config.sensor_type.value,
                    }
                )

        return sensors

    def get_simulator_status(self) -> dict[str, Any]:
        """Get status of all simulators."""
        status = {}

        for protocol, simulator in self.simulators.items():
            status[protocol] = {
                "running": getattr(simulator, "running", False),
                "sensor_count": len(self.sensor_instances),
                "update_count": getattr(simulator, "update_count", 0),
                "errors": getattr(simulator, "error_count", 0),
            }

        return status

    # PLC-aware methods

    def get_sensor_value_with_plc(self, sensor_path: str) -> dict[str, Any]:
        """Get sensor value with PLC metadata (scan cycle, quality codes, etc.).

        This method routes the sensor read through the appropriate PLC if configured.

        Args:
            sensor_path: Sensor path (e.g., "mining/crusher_1_motor_power")

        Returns:
            Dictionary with value, quality, timestamp, PLC metadata
        """
        if self.plc_manager and self.plc_manager.enabled:
            return self.plc_manager.read_sensor_value(sensor_path)
        else:
            # No PLC simulation, read directly
            value = self.get_sensor_value(sensor_path)
            return {
                "value": value,
                "quality": "Good",
                "timestamp": asyncio.get_event_loop().time(),
                "plc_name": None,
                "plc_model": None,
                "forced": False,
            }

    def get_all_plcs(self) -> dict[str, dict[str, Any]]:
        """Get information about all configured PLCs."""
        if self.plc_manager and self.plc_manager.enabled:
            return self.plc_manager.get_all_plcs()
        return {}

    def get_plc_diagnostics(self, plc_name: Optional[str] = None) -> dict[str, Any]:
        """Get PLC diagnostics.

        Args:
            plc_name: Specific PLC name, or None for all PLCs

        Returns:
            Diagnostics dictionary
        """
        if not self.plc_manager or not self.plc_manager.enabled:
            return {}

        if plc_name:
            return self.plc_manager.get_plc_diagnostics(plc_name) or {}
        else:
            return self.plc_manager.get_all_diagnostics()

    def force_sensor_value(self, sensor_path: str, value: float) -> bool:
        """Force a sensor value through its PLC.

        Args:
            sensor_path: Sensor to force
            value: Forced value

        Returns:
            True if successful, False otherwise
        """
        if self.plc_manager and self.plc_manager.enabled:
            return self.plc_manager.force_value(sensor_path, value)
        return False

    def unforce_sensor_value(self, sensor_path: str) -> bool:
        """Remove forced value from sensor.

        Args:
            sensor_path: Sensor to unforce

        Returns:
            True if successful, False otherwise
        """
        if self.plc_manager and self.plc_manager.enabled:
            return self.plc_manager.unforce_value(sensor_path)
        return False
