"""Semantic mapping for industrial sensors to SAREF/SSN/SOSA ontologies.

Maps sensor names and types to W3C WoT semantic annotations.
"""

from __future__ import annotations

from typing import Dict, List, Optional


class SemanticMapper:
    """Map sensors to semantic ontology types."""

    # Sensor type to semantic annotation mapping
    SENSOR_TYPE_MAPPINGS: Dict[str, Dict[str, str]] = {
        "temperature": {
            "@type": "saref:TemperatureSensor",
            "saref:measuresProperty": "saref:Temperature",
            "sosa:observes": "saref:Temperature",
        },
        "pressure": {
            "@type": "saref:PressureSensor",
            "saref:measuresProperty": "saref:Pressure",
            "sosa:observes": "saref:Pressure",
        },
        "power": {
            "@type": "saref:PowerSensor",
            "saref:measuresProperty": "saref:Power",
            "sosa:observes": "saref:Power",
        },
        "current": {
            "@type": "saref:ElectricitySensor",
            "saref:measuresProperty": "saref:Current",
            "sosa:observes": "saref:Current",
        },
        "voltage": {
            "@type": "saref:VoltageSensor",
            "saref:measuresProperty": "saref:Voltage",
            "sosa:observes": "saref:Voltage",
        },
        "flow": {
            "@type": "saref:Sensor",
            "saref:measuresProperty": "ex:FlowRate",
            "sosa:observes": "ex:FlowRate",
        },
        "vibration": {
            "@type": "sosa:Sensor",
            "sosa:observes": "ex:Vibration",
        },
        "level": {
            "@type": "saref:LevelSensor",
            "saref:measuresProperty": "saref:Level",
            "sosa:observes": "saref:Level",
        },
        "speed": {
            "@type": "sosa:Sensor",
            "sosa:observes": "ex:RotationalSpeed",
        },
        "humidity": {
            "@type": "saref:HumiditySensor",
            "saref:measuresProperty": "saref:Humidity",
            "sosa:observes": "saref:Humidity",
        },
        "ph": {
            "@type": "sosa:Sensor",
            "sosa:observes": "ex:pH",
        },
        "conductivity": {
            "@type": "sosa:Sensor",
            "sosa:observes": "ex:Conductivity",
        },
        "position": {
            "@type": "sosa:Sensor",
            "sosa:observes": "ex:Position",
        },
        "status": {
            "@type": "sosa:Sensor",
            "sosa:observes": "ex:Status",
        },
    }

    # Unit to QUDT URI mapping
    UNIT_URI_MAPPINGS: Dict[str, str] = {
        # Temperature
        "°C": "http://qudt.org/vocab/unit/DEG_C",
        "°F": "http://qudt.org/vocab/unit/DEG_F",
        "K": "http://qudt.org/vocab/unit/K",

        # Pressure
        "bar": "http://qudt.org/vocab/unit/BAR",
        "PSI": "http://qudt.org/vocab/unit/PSI",
        "Pa": "http://qudt.org/vocab/unit/PA",
        "kPa": "http://qudt.org/vocab/unit/KiloPA",
        "mbar": "http://qudt.org/vocab/unit/MilliBAR",
        "mTorr": "http://qudt.org/vocab/unit/MilliTORR",

        # Power
        "kW": "http://qudt.org/vocab/unit/KiloW",
        "MW": "http://qudt.org/vocab/unit/MegaW",
        "W": "http://qudt.org/vocab/unit/W",

        # Current
        "A": "http://qudt.org/vocab/unit/A",
        "kA": "http://qudt.org/vocab/unit/KiloA",

        # Voltage
        "V": "http://qudt.org/vocab/unit/V",
        "kV": "http://qudt.org/vocab/unit/KiloV",

        # Flow
        "m³/h": "http://qudt.org/vocab/unit/M3-PER-HR",
        "L/min": "http://qudt.org/vocab/unit/L-PER-MIN",
        "LPM": "http://qudt.org/vocab/unit/L-PER-MIN",
        "GPM": "http://qudt.org/vocab/unit/GAL_US-PER-MIN",
        "CFM": "http://qudt.org/vocab/unit/FT3-PER-MIN",
        "SCFM": "http://qudt.org/vocab/unit/FT3-PER-MIN",
        "BBL/day": "http://qudt.org/vocab/unit/BBL-PER-DAY",
        "MGD": "http://qudt.org/vocab/unit/MegaGAL_US-PER-DAY",
        "MMSCFD": "http://qudt.org/vocab/unit/MillionFT3-PER-DAY",
        "kg/s": "http://qudt.org/vocab/unit/KiloGM-PER-SEC",
        "kg/h": "http://qudt.org/vocab/unit/KiloGM-PER-HR",
        "g/min": "http://qudt.org/vocab/unit/GM-PER-MIN",

        # Speed
        "RPM": "http://qudt.org/vocab/unit/REV-PER-MIN",
        "Hz": "http://qudt.org/vocab/unit/HZ",
        "m/s": "http://qudt.org/vocab/unit/M-PER-SEC",
        "m/min": "http://qudt.org/vocab/unit/M-PER-MIN",
        "vehicles/h": "http://qudt.org/vocab/unit/NUM-PER-HR",
        "bottles/min": "http://qudt.org/vocab/unit/NUM-PER-MIN",
        "vials/min": "http://qudt.org/vocab/unit/NUM-PER-MIN",
        "tablets/min": "http://qudt.org/vocab/unit/NUM-PER-MIN",
        "units/min": "http://qudt.org/vocab/unit/NUM-PER-MIN",
        "deg/s": "http://qudt.org/vocab/unit/DEG-PER-SEC",

        # Vibration
        "mm/s": "http://qudt.org/vocab/unit/MilliM-PER-SEC",

        # Level / Percentage
        "%": "http://qudt.org/vocab/unit/PERCENT",
        "%RH": "http://qudt.org/vocab/unit/PERCENT",
        "ft": "http://qudt.org/vocab/unit/FT",
        "m": "http://qudt.org/vocab/unit/M",
        "mm": "http://qudt.org/vocab/unit/MilliM",
        "kg": "http://qudt.org/vocab/unit/KiloGM",
        "g": "http://qudt.org/vocab/unit/GM",
        "mg": "http://qudt.org/vocab/unit/MilliGM",
        "L": "http://qudt.org/vocab/unit/L",
        "mL": "http://qudt.org/vocab/unit/MilliL",
        "BBL": "http://qudt.org/vocab/unit/BBL",
        "kg/m³": "http://qudt.org/vocab/unit/KiloGM-PER-M3",
        "g/L": "http://qudt.org/vocab/unit/GM-PER-L",
        "ton": "http://qudt.org/vocab/unit/TON_Metric",
        "kN": "http://qudt.org/vocab/unit/KiloN",

        # Electrical
        "MVA": "http://qudt.org/vocab/unit/MegaV-A",
        "PF": "http://qudt.org/vocab/unit/NUM",

        # Angle
        "deg": "http://qudt.org/vocab/unit/DEG",
        "°": "http://qudt.org/vocab/unit/DEG",

        # Concentration / Quality
        "pH": "http://qudt.org/vocab/unit/PH",
        "ppm": "http://qudt.org/vocab/unit/PPM",
        "NTU": "http://qudt.org/vocab/unit/NTU",
        "μS/cm": "http://qudt.org/vocab/unit/MicroS-PER-CentiM",
        "mS/cm": "http://qudt.org/vocab/unit/MilliS-PER-CentiM",
        "cP": "http://qudt.org/vocab/unit/CentiPOISE",

        # Irradiance
        "W/m²": "http://qudt.org/vocab/unit/W-PER-M2",

        # Light
        "lux": "http://qudt.org/vocab/unit/LUX",

        # Rate / Ratio
        "ratio": "http://qudt.org/vocab/unit/NUM",
        "ACH": "http://qudt.org/vocab/unit/NUM-PER-HR",
        "SCF/BBL": "http://qudt.org/vocab/unit/FT3-PER-BBL",
        "kW/ton": "http://qudt.org/vocab/unit/KiloW-PER-TON_Metric",

        # Torque
        "Nm": "http://qudt.org/vocab/unit/N-M",

        # Count / Time
        "count": "http://qudt.org/vocab/unit/NUM",
        "s": "http://qudt.org/vocab/unit/SEC",
        "min": "http://qudt.org/vocab/unit/MIN",
        "floor": "http://qudt.org/vocab/unit/NUM",
        "people": "http://qudt.org/vocab/unit/NUM",
        "vehicles": "http://qudt.org/vocab/unit/NUM",
        "particles/m³": "http://qudt.org/vocab/unit/NUM-PER-M3",
        "cycles": "http://qudt.org/vocab/unit/NUM",

        # Binary
        "binary": "http://qudt.org/vocab/unit/NUM",
    }

    @classmethod
    def get_semantic_type(cls, sensor_type: str) -> List[str]:
        """Get semantic @type for sensor type.

        Args:
            sensor_type: Sensor type (e.g., "temperature", "pressure")

        Returns:
            List of semantic type URIs (includes opcua:AnalogItemType)
        """
        mapping = cls.SENSOR_TYPE_MAPPINGS.get(sensor_type.lower(), {})
        semantic_type = mapping.get("@type", "sosa:Sensor")

        # Always include OPC UA analog item type
        if isinstance(semantic_type, str):
            return [semantic_type, "opcua:AnalogItemType"]
        return semantic_type + ["opcua:AnalogItemType"]

    @classmethod
    def get_semantic_annotations(cls, sensor_type: str) -> Dict[str, str]:
        """Get all semantic annotations for sensor type.

        Args:
            sensor_type: Sensor type (e.g., "temperature", "pressure")

        Returns:
            Dict of semantic annotations
        """
        return cls.SENSOR_TYPE_MAPPINGS.get(sensor_type.lower(), {}).copy()

    @classmethod
    def get_unit_uri(cls, unit: str) -> Optional[str]:
        """Get QUDT unit URI for unit string.

        Args:
            unit: Unit string (e.g., "°C", "kW", "bar")

        Returns:
            QUDT unit URI or None if not mapped
        """
        return cls.UNIT_URI_MAPPINGS.get(unit)


# Convenience functions for module-level access
def get_semantic_type(sensor_type: str) -> List[str]:
    """Get semantic @type for sensor type."""
    return SemanticMapper.get_semantic_type(sensor_type)


def get_unit_uri(unit: str) -> Optional[str]:
    """Get QUDT unit URI for unit string."""
    return SemanticMapper.get_unit_uri(unit)
