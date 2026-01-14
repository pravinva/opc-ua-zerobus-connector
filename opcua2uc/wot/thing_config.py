"""Thing Configuration extracted from W3C WoT Thing Description."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from opcua2uc.protocols.base import ProtocolType


@dataclass
class ThingConfig:
    """Configuration extracted from W3C WoT Thing Description.

    This dataclass represents the key information parsed from a Thing Description
    that is needed to auto-configure a ProtocolClient.

    Attributes:
        name: Human-readable name from TD title
        thing_id: Unique identifier for the Thing (e.g., "urn:dev:ops:...")
        endpoint: Protocol endpoint extracted from base or forms
        protocol_type: Detected protocol (opcua, mqtt, or modbus)
        properties: List of property names from TD
        semantic_types: Mapping of property name to semantic type (e.g., "saref:TemperatureSensor")
        unit_uris: Mapping of property name to QUDT unit URI
        metadata: Full TD for reference (JSON-LD document)
    """

    name: str
    thing_id: str
    endpoint: str
    protocol_type: ProtocolType
    properties: list[str]
    semantic_types: dict[str, str]  # property_name -> @type
    unit_uris: dict[str, str]       # property_name -> unit URI
    metadata: dict[str, Any]        # Full TD

    def __repr__(self) -> str:
        """Return a readable representation."""
        return (
            f"ThingConfig(name={self.name!r}, "
            f"thing_id={self.thing_id!r}, "
            f"protocol_type={self.protocol_type.value}, "
            f"properties={len(self.properties)} total)"
        )
