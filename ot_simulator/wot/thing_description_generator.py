"""W3C WoT Thing Description Generator for OPC UA Server.

Generates compliant Thing Descriptions from OPC UA nodes following:
- OPC UA 10101 WoT Binding specification
- W3C WoT Thing Description 1.1
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .ontology_loader import OntologyLoader
from .semantic_mapper import SemanticMapper


class ThingDescriptionGenerator:
    """Generate W3C WoT Thing Descriptions from OPC UA server state."""

    def __init__(
        self,
        simulator_manager: Any,
        base_url: str = "opc.tcp://0.0.0.0:4840/ot-simulator/server/",
        namespace_uri: str = "http://databricks.com/iot-simulator",
    ):
        """Initialize Thing Description Generator.

        Args:
            simulator_manager: SimulatorManager instance with sensor access
            base_url: OPC UA server endpoint URL
            namespace_uri: OPC UA namespace URI
        """
        self.simulator_manager = simulator_manager
        self.base_url = base_url
        self.namespace_uri = namespace_uri
        self.namespace_index = 2  # Custom namespace index in OPC UA

    async def generate_td(
        self,
        include_plc_nodes: bool = False,
        node_filter: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate complete Thing Description.

        Args:
            include_plc_nodes: Include PLC hierarchy nodes (default: False for now)
            node_filter: Optional list of sensor paths to include

        Returns:
            Thing Description as dict (JSON-LD compatible)
        """
        # Generate unique Thing ID
        thing_id = f"urn:dev:ops:databricks-ot-simulator-{uuid.uuid4()}"

        # Get sensor count
        sensor_count = self._get_sensor_count()

        # Create base Thing Description structure
        td = {
            "@context": OntologyLoader.get_context(),
            "@type": "Thing",
            "id": thing_id,
            "title": "Databricks OT Data Simulator",
            "description": f"Industrial sensor simulator with {sensor_count} sensors across 16 industries",
            "created": datetime.now(timezone.utc).isoformat(),
            "modified": datetime.now(timezone.utc).isoformat(),
            "support": "https://github.com/databricks/ot-simulator",
            "base": self.base_url,
            "securityDefinitions": self._generate_security_definitions(),
            "security": ["nosec"],  # Default to no security for Phase 1
            "properties": {},
            "actions": {},
            "events": {},
        }

        # Generate properties from sensors
        await self._add_sensor_properties(td, node_filter)

        return td

    def _get_sensor_count(self) -> int:
        """Get total count of sensors.

        Returns:
            Number of sensors across all industries
        """
        try:
            # Try to get from simulator manager if available
            if hasattr(self.simulator_manager, "sensor_instances"):
                return len(self.simulator_manager.sensor_instances)
            elif hasattr(self.simulator_manager, "get_all_sensor_paths"):
                return len(self.simulator_manager.get_all_sensor_paths())
        except:
            pass

        # Default fallback based on known structure (379 sensors)
        return 379

    async def _add_sensor_properties(
        self,
        td: Dict[str, Any],
        node_filter: Optional[List[str]] = None,
    ) -> None:
        """Add sensor properties to Thing Description.

        Args:
            td: Thing Description dict to modify
            node_filter: Optional filter for sensor paths
        """
        # Get all sensors from simulator manager
        sensors = self._get_filtered_sensors(node_filter)

        for sensor_info in sensors:
            property_def = self._create_property_definition(sensor_info)
            property_name = self._sanitize_name(sensor_info["name"])
            td["properties"][property_name] = property_def

    def _get_filtered_sensors(self, node_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get filtered list of sensors from simulator manager.

        Args:
            node_filter: Optional list of sensor paths to include

        Returns:
            List of sensor info dicts
        """
        sensors = []

        try:
            # Access simulator manager's sensor_instances dict (path -> Sensor)
            if hasattr(self.simulator_manager, "sensor_instances"):
                for sensor_path, sensor_sim in self.simulator_manager.sensor_instances.items():
                    # Parse industry/sensor_name from path (e.g., "mining/crusher_1_motor_temperature")
                    parts = sensor_path.split("/", 1)
                    industry = parts[0] if len(parts) > 0 else "unknown"
                    sensor_name = parts[1] if len(parts) > 1 else sensor_path

                    sensor_info = {
                        "name": sensor_name,
                        "path": sensor_path,
                        "industry": industry,
                        "sensor_type": sensor_sim.config.sensor_type.value if hasattr(sensor_sim.config.sensor_type, "value") else str(sensor_sim.config.sensor_type),
                        "unit": sensor_sim.config.unit,
                        "min_value": sensor_sim.config.min_value,
                        "max_value": sensor_sim.config.max_value,
                        "nominal_value": sensor_sim.config.nominal_value,
                    }

                    # Apply filter if provided
                    if node_filter is None or any(f in sensor_info["name"] or f in sensor_info["industry"] or f in sensor_info["path"] for f in node_filter):
                        sensors.append(sensor_info)

        except Exception as e:
            import traceback
            print(f"Warning: Could not access simulator sensors: {e}")
            print(traceback.format_exc())

        return sensors

    def _create_property_definition(self, sensor_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create WoT Property definition from sensor info.

        Args:
            sensor_info: Dict with sensor configuration

        Returns:
            WoT Property definition
        """
        sensor_name = sensor_info["name"]
        sensor_type = sensor_info["sensor_type"]
        unit = sensor_info["unit"]
        industry = sensor_info.get("industry", "")

        # Build OPC UA node ID
        node_id = f"ns={self.namespace_index};s={industry}/{sensor_name}"
        browse_path = f"0:Root/0:Objects/{self.namespace_index}:{industry.capitalize()}/{self.namespace_index}:{sensor_name}"

        # Get semantic type annotations
        semantic_types = SemanticMapper.get_semantic_type(sensor_type)
        semantic_annotations = SemanticMapper.get_semantic_annotations(sensor_type)

        # Get unit URI
        unit_uri = SemanticMapper.get_unit_uri(unit)

        # Base property definition
        property_def = {
            "@type": semantic_types,
            "title": sensor_name.replace("_", " ").title(),
            "description": f"{sensor_type.capitalize()} sensor in {industry} industry",
            "type": "number",
            "observable": True,
            "forms": [
                {
                    "href": f"?{node_id}",
                    "opcua:nodeId": node_id,
                    "opcua:browsePath": browse_path,
                    "op": ["readproperty", "observeproperty"],
                    "contentType": "application/opcua+uadp",
                    "subprotocol": "opcua",
                }
            ],
        }

        # Add semantic annotations
        for key, value in semantic_annotations.items():
            if key != "@type":  # Already added
                property_def[key] = value

        # Add unit information
        if unit:
            property_def["unit"] = unit
        if unit_uri:
            property_def["qudt:unit"] = unit_uri

        # Add value ranges
        if "min_value" in sensor_info:
            property_def["minimum"] = sensor_info["min_value"]
        if "max_value" in sensor_info:
            property_def["maximum"] = sensor_info["max_value"]

        # Add industry context
        if industry:
            property_def["ex:industry"] = industry

        return property_def

    def _sanitize_name(self, name: str) -> str:
        """Sanitize sensor name for use as property key.

        Args:
            name: Original sensor name

        Returns:
            Sanitized name (alphanumeric + underscore)
        """
        # Replace spaces and special characters with underscores
        sanitized = name.replace(" ", "_").replace("-", "_")

        # Remove any remaining non-alphanumeric characters except underscore
        sanitized = "".join(c for c in sanitized if c.isalnum() or c == "_")

        return sanitized.lower()

    def _generate_security_definitions(self) -> Dict[str, Any]:
        """Generate security definitions for Thing Description.

        Returns:
            Security definitions dict
        """
        security_defs = {
            "nosec": {
                "scheme": "nosec",
                "description": "No security - for testing and development only",
            }
        }

        # TODO: Add Basic256Sha256 security definition in Phase 2
        # if self.security_policy == "Basic256Sha256":
        #     security_defs["opcua_channel"] = {
        #         "scheme": "OPCUASecurityChannelScheme",
        #         "securityPolicy": "Basic256Sha256",
        #         "securityMode": "SignAndEncrypt",
        #         "in": "header",
        #         "description": "OPC UA secure channel with encryption"
        #     }

        return security_defs

    def generate_compact_td(self, full_td: Dict[str, Any]) -> Dict[str, Any]:
        """Generate compact version of Thing Description.

        Args:
            full_td: Full Thing Description

        Returns:
            Compact Thing Description (summary only)
        """
        return {
            "@context": full_td["@context"],
            "@type": full_td["@type"],
            "id": full_td["id"],
            "title": full_td["title"],
            "description": full_td["description"],
            "base": full_td["base"],
            "security": full_td["security"],
            "propertyCount": len(full_td.get("properties", {})),
            "actionCount": len(full_td.get("actions", {})),
            "eventCount": len(full_td.get("events", {})),
            "links": [
                {
                    "rel": "full-thing-description",
                    "href": f"{full_td['base']}/thing-description",
                    "type": "application/td+json",
                }
            ],
        }
