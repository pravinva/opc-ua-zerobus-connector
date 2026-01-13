"""PLC Manager - loads and manages PLC instances from configuration.

Responsibilities:
- Load plc_config.yaml
- Create PLC instances for each configured PLC
- Route sensor reads through appropriate PLCs
- Provide PLC-aware sensor access
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml

from ot_simulator.plc_models import (
    PLCVendor,
    PLCSimulator,
    create_plc_from_model,
)
from ot_simulator.sensor_models import IndustryType

logger = logging.getLogger("ot_simulator.plc_manager")


class PLCManager:
    """Manages multiple PLC instances and routes sensor access through them."""

    def __init__(self, simulator_manager, config_path: Optional[str] = None):
        """Initialize PLC manager.

        Args:
            simulator_manager: Reference to SimulatorManager for sensor access
            config_path: Path to plc_config.yaml (defaults to ot_simulator/plc_config.yaml)
        """
        self.simulator_manager = simulator_manager
        self.plcs: dict[str, PLCSimulator] = {}  # plc_name -> PLCSimulator
        self.industry_to_plc: dict[str, str] = {}  # industry_name -> plc_name
        self.enabled = False
        self.global_settings = {}

        # Default config path
        if config_path is None:
            config_path = Path(__file__).parent / "plc_config.yaml"
        self.config_path = config_path

    def load_config(self) -> bool:
        """Load PLC configuration from YAML.

        Returns:
            True if config loaded successfully, False otherwise
        """
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"PLC config not found at {self.config_path}, PLCs disabled")
                self.enabled = False
                return False

            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)

            if not config:
                logger.warning("Empty PLC config, PLCs disabled")
                self.enabled = False
                return False

            # Load global settings
            self.global_settings = config.get("global_plc_settings", {})
            self.enabled = self.global_settings.get("enable_plc_simulation", True)

            if not self.enabled:
                logger.info("PLC simulation disabled in config")
                return False

            # Load PLC instances
            plc_configs = config.get("plcs", {})
            logger.info(f"Loading {len(plc_configs)} PLCs from config...")

            for plc_name, plc_config in plc_configs.items():
                # Skip disabled PLCs
                if not plc_config.get("enabled", True):
                    logger.info(f"Skipping disabled PLC: {plc_name}")
                    continue

                try:
                    # Extract config values
                    vendor_str = plc_config["vendor"]
                    model = plc_config["model"]
                    industries = plc_config.get("industries", [])

                    # Convert vendor string to enum
                    vendor = PLCVendor(vendor_str)

                    # Create PLC instance
                    plc = create_plc_from_model(
                        vendor=vendor,
                        model=model,
                        name=plc_name,
                        assigned_industries=industries,
                        sensor_manager=self.simulator_manager,
                    )

                    # Apply global settings if configured
                    if "simulate_scan_delays" in self.global_settings:
                        plc.config.simulate_scan_delay = self.global_settings["simulate_scan_delays"]
                    if "simulate_quality_issues" in self.global_settings:
                        plc.config.simulate_quality_issues = self.global_settings["simulate_quality_issues"]
                        plc.config.quality_issue_probability = self.global_settings.get(
                            "quality_issue_probability", 0.0005
                        )
                    if "simulate_comm_failures" in self.global_settings:
                        plc.config.simulate_comm_failures = self.global_settings["simulate_comm_failures"]
                        plc.config.comm_failure_probability = self.global_settings.get(
                            "comm_failure_probability", 0.0001
                        )
                    if "allow_forcing" in self.global_settings:
                        # Only enable if both global and model support it
                        plc.config.supports_forcing = (
                            plc.config.supports_forcing and self.global_settings["allow_forcing"]
                        )

                    # Store PLC
                    self.plcs[plc_name] = plc

                    # Build industry mapping
                    for industry in industries:
                        self.industry_to_plc[industry] = plc_name
                        logger.debug(f"  Mapped industry '{industry}' to {plc_name}")

                    logger.info(
                        f"✓ Loaded {plc_name}: {vendor.value} {model} "
                        f"(industries: {', '.join(industries)})"
                    )

                except Exception as e:
                    logger.error(f"Failed to load PLC {plc_name}: {e}", exc_info=True)
                    continue

            logger.info(f"✓ PLC Manager initialized with {len(self.plcs)} active PLCs")
            return True

        except Exception as e:
            logger.error(f"Failed to load PLC config: {e}", exc_info=True)
            self.enabled = False
            return False

    def get_plc_for_sensor(self, sensor_path: str) -> Optional[PLCSimulator]:
        """Get the PLC that controls a given sensor.

        Args:
            sensor_path: Sensor path (e.g., "mining/crusher_1_motor_power")

        Returns:
            PLCSimulator instance or None if no PLC assigned
        """
        if not self.enabled or not self.plcs:
            return None

        # Extract industry from sensor path
        parts = sensor_path.split("/")
        if len(parts) < 2:
            return None

        industry = parts[0]

        # Look up PLC for this industry
        plc_name = self.industry_to_plc.get(industry)
        if not plc_name:
            return None

        return self.plcs.get(plc_name)

    def read_sensor_value(self, sensor_path: str) -> dict[str, Any]:
        """Read sensor value through appropriate PLC (if configured).

        Args:
            sensor_path: Sensor path (e.g., "mining/crusher_1_motor_power")

        Returns:
            Dictionary with value, quality, timestamp, PLC metadata
        """
        plc = self.get_plc_for_sensor(sensor_path)

        if plc is None:
            # No PLC configured, read directly from simulator
            value = self.simulator_manager.get_sensor_value(sensor_path)
            return {
                "value": value,
                "quality": "Good",
                "timestamp": None,  # Will be set by caller
                "plc_name": None,
                "plc_model": None,
                "forced": False,
            }

        # Read through PLC (adds scan cycle, quality codes, etc.)
        return plc.read_input(sensor_path)

    def force_value(self, sensor_path: str, value: float) -> bool:
        """Force a sensor value through its PLC.

        Args:
            sensor_path: Sensor to force
            value: Forced value

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.warning("PLC simulation disabled, cannot force values")
            return False

        plc = self.get_plc_for_sensor(sensor_path)
        if plc is None:
            logger.warning(f"No PLC assigned to {sensor_path}, cannot force")
            return False

        plc.force_value(sensor_path, value)
        return True

    def unforce_value(self, sensor_path: str) -> bool:
        """Remove forced value from sensor.

        Args:
            sensor_path: Sensor to unforce

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False

        plc = self.get_plc_for_sensor(sensor_path)
        if plc is None:
            return False

        plc.unforce_value(sensor_path)
        return True

    def get_all_plcs(self) -> dict[str, dict[str, Any]]:
        """Get information about all PLCs.

        Returns:
            Dictionary mapping plc_name to PLC info
        """
        result = {}
        for plc_name, plc in self.plcs.items():
            result[plc_name] = {
                "name": plc_name,
                "vendor": plc.config.vendor.value,
                "model": plc.config.model,
                "industries": plc.config.assigned_industries,
                "scan_cycle_ms": plc.config.scan_cycle_ms,
                "run_mode": plc.run_mode.value,
                "supports_forcing": plc.config.supports_forcing,
                "supports_diagnostics": plc.config.supports_diagnostics,
                "rack": plc.config.rack,
                "slot": plc.config.slot,
            }
        return result

    def get_plc_diagnostics(self, plc_name: str) -> Optional[dict[str, Any]]:
        """Get diagnostics for a specific PLC.

        Args:
            plc_name: Name of PLC

        Returns:
            Diagnostics dictionary or None if not found
        """
        plc = self.plcs.get(plc_name)
        if plc is None:
            return None

        return plc.get_diagnostics()

    def get_all_diagnostics(self) -> dict[str, dict[str, Any]]:
        """Get diagnostics for all PLCs.

        Returns:
            Dictionary mapping plc_name to diagnostics
        """
        result = {}
        for plc_name, plc in self.plcs.items():
            result[plc_name] = plc.get_diagnostics()
        return result
