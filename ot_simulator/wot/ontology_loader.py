"""Ontology definitions and loaders for W3C WoT semantic annotations.

Provides ontology context definitions for:
- SAREF: Smart Applications REFerence ontology
- SSN/SOSA: Semantic Sensor Network
- QUDT: Quantities, Units, Dimensions and Types
- OPC UA: OPC Foundation OPC UA vocabulary
"""

from __future__ import annotations

from typing import Dict, List


class OntologyLoader:
    """Load and manage ontology contexts for Thing Descriptions."""

    # W3C WoT Thing Description base context
    WOT_TD_CONTEXT = "https://www.w3.org/2022/wot/td/v1.1"

    # Standard ontology prefixes and URIs
    ONTOLOGY_CONTEXTS: Dict[str, str] = {
        # Core WoT vocabularies
        "td": "https://www.w3.org/2019/wot/td#",
        "jsonschema": "https://www.w3.org/2019/wot/json-schema#",
        "wotsec": "https://www.w3.org/2019/wot/security#",

        # Semantic ontologies
        "saref": "https://saref.etsi.org/core/",
        "sosa": "http://www.w3.org/ns/sosa/",
        "ssn": "http://www.w3.org/ns/ssn/",
        "qudt": "http://qudt.org/schema/qudt/",
        "unit": "http://qudt.org/vocab/unit/",

        # OPC UA vocabulary
        "opcua": "http://opcfoundation.org/UA/",

        # Generic vocabularies
        "schema": "https://schema.org/",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",

        # Custom extensions (example namespace)
        "ex": "http://example.org/",
    }

    @classmethod
    def get_context(cls) -> List[Dict[str, str] | str]:
        """Get full @context for Thing Description.

        Returns:
            List containing WoT TD base context and ontology mappings
        """
        return [
            cls.WOT_TD_CONTEXT,
            cls.ONTOLOGY_CONTEXTS.copy(),
        ]

    @classmethod
    def get_ontology_prefixes(cls) -> Dict[str, str]:
        """Get ontology prefix to URI mappings.

        Returns:
            Dict of prefix -> URI mappings
        """
        return cls.ONTOLOGY_CONTEXTS.copy()

    @classmethod
    def expand_curie(cls, curie: str) -> str:
        """Expand CURIE to full URI.

        Args:
            curie: Compact URI (e.g., "saref:TemperatureSensor")

        Returns:
            Full URI (e.g., "https://saref.etsi.org/core/TemperatureSensor")
        """
        if ":" not in curie:
            return curie

        prefix, local_name = curie.split(":", 1)
        base_uri = cls.ONTOLOGY_CONTEXTS.get(prefix)

        if base_uri:
            return f"{base_uri}{local_name}"
        return curie

    @classmethod
    def get_saref_terms(cls) -> List[str]:
        """Get commonly used SAREF terms.

        Returns:
            List of SAREF terms
        """
        return [
            "saref:TemperatureSensor",
            "saref:PressureSensor",
            "saref:PowerSensor",
            "saref:ElectricitySensor",
            "saref:VoltageSensor",
            "saref:HumiditySensor",
            "saref:LevelSensor",
            "saref:Sensor",
            "saref:Actuator",
            "saref:Temperature",
            "saref:Pressure",
            "saref:Power",
            "saref:Current",
            "saref:Voltage",
            "saref:Humidity",
            "saref:Level",
            "saref:measuresProperty",
            "saref:hasUnit",
        ]

    @classmethod
    def get_sosa_terms(cls) -> List[str]:
        """Get commonly used SOSA/SSN terms.

        Returns:
            List of SOSA/SSN terms
        """
        return [
            "sosa:Sensor",
            "sosa:Actuator",
            "sosa:Observation",
            "sosa:observes",
            "sosa:madeObservation",
            "sosa:hasResult",
            "sosa:resultTime",
            "sosa:hasFeatureOfInterest",
            "sosa:madeBySensor",
            "ssn:System",
            "ssn:hasProperty",
        ]

    @classmethod
    def get_qudt_terms(cls) -> List[str]:
        """Get commonly used QUDT terms.

        Returns:
            List of QUDT terms
        """
        return [
            "qudt:QuantityValue",
            "qudt:numericValue",
            "qudt:unit",
            "qudt:hasUnit",
            "unit:DEG_C",
            "unit:BAR",
            "unit:KiloW",
            "unit:A",
            "unit:V",
            "unit:M-PER-SEC",
        ]


# Module-level convenience
def get_context() -> List[Dict[str, str] | str]:
    """Get full @context for Thing Description."""
    return OntologyLoader.get_context()


def get_ontology_prefixes() -> Dict[str, str]:
    """Get ontology prefix to URI mappings."""
    return OntologyLoader.get_ontology_prefixes()
