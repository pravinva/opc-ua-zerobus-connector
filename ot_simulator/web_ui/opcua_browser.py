"""OPC-UA hierarchy browser logic.

This module handles building and serving the OPC-UA node hierarchy tree structure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aiohttp import web

from ot_simulator.sensor_models import IndustryType

if TYPE_CHECKING:
    from ot_simulator.simulator_manager import SimulatorManager


class OPCUABrowser:
    """Handles OPC-UA hierarchy browsing functionality."""

    def __init__(self, config: Any, simulator_manager: SimulatorManager):
        """Initialize OPC-UA browser.

        Args:
            config: Simulator configuration
            simulator_manager: SimulatorManager instance
        """
        self.config = config
        self.manager = simulator_manager

    async def handle_opcua_hierarchy(self, request: web.Request) -> web.Response:
        """Return OPC-UA node hierarchy as JSON tree structure.

        Returns:
            JSON structure representing Objects/PLCs/[PLC_NAME]/Diagnostics and Inputs hierarchy
        """
        hierarchy = self.build_hierarchy()
        return web.json_response(hierarchy)

    def build_hierarchy(self) -> dict[str, Any]:
        """Build the complete OPC-UA hierarchy tree with both PLCs and IndustrialSensors views.

        Returns:
            Dictionary representing the OPC-UA node hierarchy
        """
        hierarchy = {
            "root": "Objects",
            "children": []
        }

        # Build IndustrialSensors folder (industry-based view)
        industrial_sensors_folder = {
            "name": "IndustrialSensors",
            "type": "folder",
            "children": []
        }
        self._build_simple_hierarchy(industrial_sensors_folder)
        hierarchy['children'].append(industrial_sensors_folder)

        # Build PLCs folder (PLC-based view)
        all_plcs = self.manager.get_all_plcs()
        if all_plcs:
            plcs_folder = {
                "name": "PLCs",
                "type": "folder",
                "children": []
            }
            for plc_name, plc_info in all_plcs.items():
                plc_node = self._build_plc_node(plc_name, plc_info)
                plcs_folder['children'].append(plc_node)
            hierarchy['children'].append(plcs_folder)

        return hierarchy

    def _build_plc_node(self, plc_name: str, plc_info: dict[str, Any]) -> dict[str, Any]:
        """Build a PLC node with diagnostics and inputs.

        Args:
            plc_name: Name of the PLC
            plc_info: PLC metadata

        Returns:
            Dictionary representing the PLC node
        """
        # Create PLC node
        plc_display_name = f"{plc_name} ({plc_info['vendor'].title()} {plc_info['model']})"
        plc_node = {
            "name": plc_display_name,
            "type": "plc",
            "children": []
        }

        # Add Diagnostics folder
        diagnostics = self.manager.get_plc_diagnostics(plc_name)
        if diagnostics:
            diagnostics_node = {
                "name": "Diagnostics",
                "type": "folder",
                "properties": {
                    "Vendor": plc_info['vendor'],
                    "Model": plc_info['model'],
                    "RunMode": diagnostics.get('run_mode', 'UNKNOWN'),
                    "ScanCycleMs": plc_info.get('scan_cycle_ms', 'N/A'),
                    "TotalScans": diagnostics.get('total_scans', 0),
                    "ForcedValues": diagnostics.get('forced_value_count', 0),
                    "QualityIssues": diagnostics.get('quality_issue_count', 0),
                    "CommFailures": diagnostics.get('comm_failure_count', 0)
                }
            }
            plc_node['children'].append(diagnostics_node)

        # Add Inputs folder with industry subfolders
        inputs_folder = {
            "name": "Inputs",
            "type": "folder",
            "children": []
        }

        # Group sensors by industry for this PLC
        for industry_name in plc_info.get('industries', []):
            industry_sensors = self.manager.get_sensors_by_industry(industry_name)

            if industry_sensors:
                industry_node = self._build_industry_node(industry_name, industry_sensors)
                inputs_folder['children'].append(industry_node)

        if inputs_folder['children']:
            plc_node['children'].append(inputs_folder)

        return plc_node

    def _build_industry_node(self, industry_name: str, industry_sensors: list[Any]) -> dict[str, Any]:
        """Build an industry node with its sensors.

        Args:
            industry_name: Name of the industry
            industry_sensors: List of sensor info dictionaries from get_sensors_by_industry()

        Returns:
            Dictionary representing the industry node
        """
        # Create industry folder
        industry_node = {
            "name": industry_name.replace("_", " ").title(),
            "type": "industry",
            "children": []
        }

        # Add sensors
        for sensor_info in industry_sensors:
            sensor_node = self._build_sensor_node(sensor_info)
            industry_node['children'].append(sensor_node)

        return industry_node

    def _build_sensor_node(self, sensor_info: dict[str, Any]) -> dict[str, Any]:
        """Build a sensor node with current value and metadata.

        Args:
            sensor_info: Dictionary containing sensor information from get_sensors_by_industry()
                        with keys: path, name, min_value, max_value, unit, type

        Returns:
            Dictionary representing the sensor node
        """
        # Get sensor path from the info dict
        sensor_path = sensor_info['path']

        # Get current sensor value with PLC metadata
        sensor_data = self.manager.get_sensor_value_with_plc(sensor_path)

        sensor_node = {
            "name": sensor_info['name'],
            "type": "sensor",
            "path": sensor_path,
            "value": sensor_data.get('value', 0),
            "unit": sensor_info['unit'],
            "quality": sensor_data.get('quality', 'Good'),
            "forced": sensor_data.get('forced', False),
            "min_value": sensor_info['min_value'],
            "max_value": sensor_info['max_value']
        }
        return sensor_node

    def _build_simple_hierarchy(self, plcs_folder: dict[str, Any]) -> None:
        """Build a simple hierarchy directly from sensors without PLCs.

        Args:
            plcs_folder: The PLCs folder to populate
        """
        # Group by industry directly under PLCs
        for industry in IndustryType:
            industry_sensors = self.manager.get_sensors_by_industry(industry.value)

            if industry_sensors:
                industry_node = {
                    "name": industry.value.replace("_", " ").title(),
                    "type": "industry",
                    "children": []
                }

                for sensor_info in industry_sensors:
                    # Get sensor path from the info dict
                    sensor_path = sensor_info['path']
                    value = self.manager.get_sensor_value(sensor_path)
                    sensor_node = {
                        "name": sensor_info['name'],
                        "type": "sensor",
                        "path": sensor_path,
                        "value": value if value is not None else 0,
                        "unit": sensor_info['unit'],
                        "quality": "Good",
                        "forced": False,
                        "min_value": sensor_info['min_value'],
                        "max_value": sensor_info['max_value']
                    }
                    industry_node['children'].append(sensor_node)

                plcs_folder['children'].append(industry_node)
