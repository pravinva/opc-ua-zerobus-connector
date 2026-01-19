"""W3C Web of Things (WoT) integration for OT Data Simulator.

This module provides:
- Thing Description generation from OPC UA nodes
- Semantic annotations (SAREF, SSN/SOSA ontologies)
- OPC UA 10101 WoT Binding compliance
"""

from .thing_description_generator import ThingDescriptionGenerator
from .semantic_mapper import SemanticMapper, get_semantic_type, get_unit_uri
from .ontology_loader import OntologyLoader

__all__ = [
    "ThingDescriptionGenerator",
    "SemanticMapper",
    "OntologyLoader",
    "get_semantic_type",
    "get_unit_uri",
]
