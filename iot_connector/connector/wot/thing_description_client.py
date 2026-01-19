"""Client for fetching and parsing W3C WoT Thing Descriptions."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from opcua2uc.protocols.base import ProtocolType
from opcua2uc.wot.thing_config import ThingConfig

logger = logging.getLogger(__name__)


class ThingDescriptionClient:
    """Fetch and parse W3C WoT Thing Descriptions.

    This client fetches Thing Descriptions (TDs) from HTTP endpoints and
    parses them into ThingConfig objects that can be used to auto-configure
    ProtocolClients.

    Example usage:
        >>> client = ThingDescriptionClient()
        >>> td = await client.fetch_td("http://simulator:8000/api/opcua/thing-description")
        >>> config = client.parse_td(td)
        >>> print(config.protocol_type)  # ProtocolType.OPCUA
    """

    async def fetch_td(self, url: str, timeout: float = 10.0) -> dict[str, Any]:
        """Fetch Thing Description from HTTP endpoint.

        Args:
            url: HTTP URL to fetch TD from
            timeout: Request timeout in seconds (default: 10.0)

        Returns:
            Thing Description as a dictionary (JSON-LD)

        Raises:
            httpx.HTTPError: If request fails
            ValueError: If response is not valid JSON
        """
        logger.info(f"Fetching Thing Description from {url}")

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()

            td = response.json()
            logger.info(f"Successfully fetched TD: {td.get('title', 'unknown')}")
            return td

    def parse_td(self, td: dict[str, Any]) -> ThingConfig:
        """Parse Thing Description into ThingConfig.

        Extracts key information from a W3C WoT Thing Description:
        - Protocol type (from forms hrefs)
        - Endpoint/base URL
        - Properties
        - Semantic types (@type annotations)
        - Unit URIs (QUDT units)

        Args:
            td: Thing Description dictionary (JSON-LD)

        Returns:
            ThingConfig with extracted configuration

        Raises:
            ValueError: If TD is missing required fields or has invalid format
        """
        # Extract basic metadata
        name = td.get("title", "unknown")
        thing_id = td.get("id", "")

        if not thing_id:
            raise ValueError("Thing Description missing required 'id' field")

        # Extract base URL and properties
        base = td.get("base", "")
        properties = td.get("properties", {})

        if not properties:
            raise ValueError("Thing Description has no properties")

        # Detect protocol from base URL (not from relative hrefs)
        if not base:
            raise ValueError("Thing Description missing 'base' URL")

        protocol_type = self._detect_protocol_from_href(base)

        # Use base URL as endpoint
        endpoint = base

        # Extract semantic types and unit URIs from properties
        semantic_types: dict[str, str] = {}
        unit_uris: dict[str, str] = {}

        for prop_name, prop_def in properties.items():
            # Extract semantic type (@type field)
            if "@type" in prop_def:
                semantic_type = prop_def["@type"]
                # Handle both string and list of strings
                if isinstance(semantic_type, list):
                    semantic_types[prop_name] = semantic_type[0] if semantic_type else ""
                else:
                    semantic_types[prop_name] = semantic_type

            # Extract unit URI
            if "unit" in prop_def:
                unit_uris[prop_name] = prop_def["unit"]

        logger.info(
            f"Parsed TD '{name}': {len(properties)} properties, "
            f"{len(semantic_types)} with semantic types, "
            f"protocol={protocol_type.value}"
        )

        return ThingConfig(
            name=name,
            thing_id=thing_id,
            endpoint=endpoint,
            protocol_type=protocol_type,
            properties=list(properties.keys()),
            semantic_types=semantic_types,
            unit_uris=unit_uris,
            metadata=td,
        )

    def _detect_protocol_from_href(self, href: str) -> ProtocolType:
        """Detect protocol type from form href.

        Args:
            href: Form href URL

        Returns:
            Detected protocol type

        Raises:
            ValueError: If protocol cannot be detected
        """
        href_lower = href.lower().strip()

        if href_lower.startswith("opc.tcp://"):
            return ProtocolType.OPCUA
        elif href_lower.startswith("mqtt://") or href_lower.startswith("mqtts://"):
            return ProtocolType.MQTT
        elif href_lower.startswith("modbus://") or href_lower.startswith("modbustcp://"):
            return ProtocolType.MODBUS
        else:
            raise ValueError(f"Cannot detect protocol from href: {href}")

    def _extract_endpoint_from_href(self, href: str) -> str:
        """Extract base endpoint from href.

        For OPC-UA: Extract "opc.tcp://host:port" from full path
        For MQTT: Extract "mqtt://host:port" from topic
        For Modbus: Extract "modbus://host:port" from full address

        Args:
            href: Form href URL

        Returns:
            Base endpoint without path/topic/address
        """
        # For OPC-UA, extract base endpoint
        if href.startswith("opc.tcp://"):
            # href might be "opc.tcp://host:port" or "opc.tcp://host:port/path"
            # Extract just the protocol://host:port part
            parts = href.split("/", 3)
            if len(parts) >= 3:
                return f"{parts[0]}//{parts[2]}"
            return href

        # For MQTT, extract broker endpoint
        elif href.startswith("mqtt://") or href.startswith("mqtts://"):
            parts = href.split("/", 3)
            if len(parts) >= 3:
                return f"{parts[0]}//{parts[2]}"
            return href

        # For Modbus, extract TCP endpoint
        elif href.startswith("modbus://") or href.startswith("modbustcp://"):
            parts = href.split("/", 3)
            if len(parts) >= 3:
                return f"{parts[0]}//{parts[2]}"
            return href

        # Fallback: return as-is
        return href
