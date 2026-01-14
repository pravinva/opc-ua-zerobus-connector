"""Bridge between W3C WoT Thing Descriptions and ProtocolClient."""
from __future__ import annotations

import logging
from typing import Any, Callable

from opcua2uc.protocols.base import ProtocolClient, ProtocolRecord, ProtocolType
from opcua2uc.protocols.factory import create_protocol_client
from opcua2uc.wot.thing_config import ThingConfig
from opcua2uc.wot.thing_description_client import ThingDescriptionClient

logger = logging.getLogger(__name__)


class WoTBridge:
    """Bridge between Thing Descriptions and ProtocolClient.

    This bridge fetches Thing Descriptions, parses them, and creates
    appropriate ProtocolClient instances with semantic metadata automatically
    attached to records.

    Example usage:
        >>> bridge = WoTBridge()
        >>> client = await bridge.create_client_from_td(
        ...     "http://simulator:8000/api/opcua/thing-description",
        ...     on_record_callback
        ... )
        >>> await client.connect()
    """

    def __init__(self):
        """Initialize WoT Bridge."""
        self.td_client = ThingDescriptionClient()

    async def create_client_from_td(
        self,
        td_url: str,
        on_record: Callable[[ProtocolRecord], None],
        on_stats: Callable[[dict[str, Any]], None] | None = None,
    ) -> ProtocolClient:
        """Create ProtocolClient from Thing Description URL.

        This method:
        1. Fetches TD from URL
        2. Parses TD to determine protocol (OPC-UA/MQTT/Modbus)
        3. Extracts endpoint, properties, semantic types
        4. Creates appropriate ProtocolClient
        5. Wraps on_record to add semantic metadata

        Args:
            td_url: HTTP URL to fetch Thing Description from
            on_record: Callback for received records
            on_stats: Optional callback for stats updates

        Returns:
            ProtocolClient instance configured from TD

        Raises:
            httpx.HTTPError: If TD fetch fails
            ValueError: If TD is invalid or protocol not supported
        """
        # Fetch and parse TD
        td = await self.td_client.fetch_td(td_url)
        thing_config = self.td_client.parse_td(td)

        logger.info(
            f"Creating ProtocolClient from TD: {thing_config.name} "
            f"({thing_config.protocol_type.value})"
        )

        # Create protocol-specific config
        config = self._create_protocol_config(thing_config)

        # Wrap on_record to add semantic metadata
        wrapped_on_record = self._wrap_on_record(on_record, thing_config)

        # Create ProtocolClient using existing factory
        client = create_protocol_client(
            protocol_type=thing_config.protocol_type,
            source_name=thing_config.name,
            endpoint=thing_config.endpoint,
            config=config,
            on_record=wrapped_on_record,
            on_stats=on_stats,
        )

        return client

    def _create_protocol_config(self, thing_config: ThingConfig) -> dict[str, Any]:
        """Create protocol-specific config from ThingConfig.

        Extracts protocol-specific settings from Thing Description metadata
        and creates a config dict suitable for ProtocolClient.

        Args:
            thing_config: Parsed Thing Description

        Returns:
            Protocol-specific configuration dict
        """
        config: dict[str, Any] = {
            "thing_id": thing_config.thing_id,
            "semantic_types": thing_config.semantic_types,
            "unit_uris": thing_config.unit_uris,
            "td_metadata": thing_config.metadata,
        }

        # Protocol-specific defaults
        if thing_config.protocol_type == ProtocolType.OPCUA:
            # OPC-UA specific config
            config["variable_limit"] = len(thing_config.properties)
            config["publishing_interval_ms"] = 1000
            config["reconnect_enabled"] = True

            # Extract OPC-UA node IDs from property forms (if available)
            node_ids = self._extract_opcua_node_ids(thing_config)
            if node_ids:
                config["node_ids"] = node_ids

        elif thing_config.protocol_type == ProtocolType.MQTT:
            # MQTT specific config
            topics = self._extract_mqtt_topics(thing_config)
            config["topics"] = topics if topics else ["#"]  # Default to all topics
            config["qos"] = 0
            config["reconnect_enabled"] = True

        elif thing_config.protocol_type == ProtocolType.MODBUS:
            # Modbus specific config
            registers = self._extract_modbus_registers(thing_config)
            config["registers"] = registers
            config["unit_id"] = 1  # Default unit ID
            config["poll_interval_ms"] = 1000
            config["reconnect_enabled"] = True

        return config

    def _extract_opcua_node_ids(self, thing_config: ThingConfig) -> list[str]:
        """Extract OPC-UA node IDs from Thing Description forms.

        Args:
            thing_config: Parsed Thing Description

        Returns:
            List of OPC-UA node IDs (e.g., ["ns=2;s=Temperature", ...])
        """
        node_ids = []
        properties = thing_config.metadata.get("properties", {})

        for prop_name, prop_def in properties.items():
            forms = prop_def.get("forms", [])
            for form in forms:
                # Check for opcua:nodeId in form
                if "opcua:nodeId" in form:
                    node_ids.append(form["opcua:nodeId"])
                    break

        return node_ids

    def _extract_mqtt_topics(self, thing_config: ThingConfig) -> list[str]:
        """Extract MQTT topics from Thing Description forms.

        Args:
            thing_config: Parsed Thing Description

        Returns:
            List of MQTT topics
        """
        topics = []
        properties = thing_config.metadata.get("properties", {})

        for prop_name, prop_def in properties.items():
            forms = prop_def.get("forms", [])
            for form in forms:
                href = form.get("href", "")
                # Extract topic from MQTT href (e.g., "mqtt://broker/topic/name")
                if href.startswith("mqtt://") or href.startswith("mqtts://"):
                    parts = href.split("/", 3)
                    if len(parts) >= 4:
                        topic = parts[3]
                        if topic and topic not in topics:
                            topics.append(topic)
                    break

        return topics

    def _extract_modbus_registers(self, thing_config: ThingConfig) -> list[dict[str, Any]]:
        """Extract Modbus register configurations from Thing Description.

        Args:
            thing_config: Parsed Thing Description

        Returns:
            List of register configurations
        """
        registers = []
        properties = thing_config.metadata.get("properties", {})

        for prop_name, prop_def in properties.items():
            forms = prop_def.get("forms", [])
            for form in forms:
                # Check for modbus-specific metadata
                if "modbus:address" in form:
                    register = {
                        "type": form.get("modbus:function", "holding"),
                        "address": form["modbus:address"],
                        "count": form.get("modbus:quantity", 1),
                        "name": prop_name,
                    }

                    # Extract scale factor if available
                    if "modbus:scale" in form:
                        register["scale"] = form["modbus:scale"]

                    registers.append(register)
                    break

        # If no explicit register config found, create default config
        if not registers and thing_config.protocol_type == ProtocolType.MODBUS:
            # Create default register config (holding registers starting at 0)
            for i, prop_name in enumerate(thing_config.properties):
                registers.append({
                    "type": "holding",
                    "address": i,
                    "count": 1,
                    "name": prop_name,
                })

        return registers

    def _wrap_on_record(
        self,
        on_record: Callable[[ProtocolRecord], None],
        thing_config: ThingConfig,
    ) -> Callable[[ProtocolRecord], None]:
        """Wrap on_record callback to add semantic metadata.

        This wrapper enriches ProtocolRecord instances with semantic metadata
        extracted from the Thing Description before passing them to the
        original callback.

        Args:
            on_record: Original callback
            thing_config: Parsed Thing Description

        Returns:
            Wrapped callback that adds semantic metadata
        """

        def wrapped(record: ProtocolRecord) -> None:
            # Add Thing metadata
            record.thing_id = thing_config.thing_id
            record.thing_title = thing_config.name

            # Extract property name from topic_or_path
            # This works for OPC-UA browse paths and MQTT topics
            property_name = record.topic_or_path

            # Add semantic type if available
            if property_name in thing_config.semantic_types:
                record.semantic_type = thing_config.semantic_types[property_name]

            # Add unit URI if available
            if property_name in thing_config.unit_uris:
                record.unit_uri = thing_config.unit_uris[property_name]

            # Call original callback with enriched record
            on_record(record)

        return wrapped
