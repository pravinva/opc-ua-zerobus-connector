"""Basic tests for W3C WoT Thing Description module.

Run with: python -m pytest ot_simulator/wot/test_wot_basic.py -v
"""

import pytest
from typing import Dict, Any

# Import the WoT module components
from . import (
    ThingDescriptionGenerator,
    SemanticMapper,
    OntologyLoader,
    get_semantic_type,
    get_unit_uri
)


class TestSemanticMapper:
    """Test semantic type and unit URI mappings."""

    def test_temperature_sensor_mapping(self):
        """Test temperature sensor semantic mapping."""
        semantic_types = get_semantic_type("temperature")
        assert "saref:TemperatureSensor" in semantic_types
        assert "opcua:AnalogItemType" in semantic_types

    def test_pressure_sensor_mapping(self):
        """Test pressure sensor semantic mapping."""
        semantic_types = get_semantic_type("pressure")
        assert "saref:PressureSensor" in semantic_types

    def test_power_sensor_mapping(self):
        """Test power sensor semantic mapping."""
        semantic_types = get_semantic_type("power")
        assert "saref:PowerSensor" in semantic_types

    def test_all_sensor_types_mapped(self):
        """Test that all sensor types have mappings."""
        sensor_types = [
            "temperature", "pressure", "power", "current", "voltage",
            "flow", "vibration", "level", "speed", "humidity",
            "ph", "conductivity", "position", "status"
        ]
        for sensor_type in sensor_types:
            types = get_semantic_type(sensor_type)
            assert len(types) >= 1, f"No mapping for {sensor_type}"
            assert "opcua:AnalogItemType" in types

    def test_celsius_unit_uri(self):
        """Test Celsius unit URI mapping."""
        unit_uri = get_unit_uri("°C")
        assert unit_uri == "http://qudt.org/vocab/unit/DEG_C"

    def test_kilowatt_unit_uri(self):
        """Test kilowatt unit URI mapping."""
        unit_uri = get_unit_uri("kW")
        assert unit_uri == "http://qudt.org/vocab/unit/KiloW"

    def test_bar_unit_uri(self):
        """Test bar (pressure) unit URI mapping."""
        unit_uri = get_unit_uri("bar")
        assert unit_uri == "http://qudt.org/vocab/unit/BAR"

    def test_rpm_unit_uri(self):
        """Test RPM unit URI mapping."""
        unit_uri = get_unit_uri("RPM")
        assert unit_uri == "http://qudt.org/vocab/unit/REV-PER-MIN"

    def test_unknown_unit_returns_none(self):
        """Test that unknown units return None."""
        unit_uri = get_unit_uri("UNKNOWN_UNIT")
        assert unit_uri is None

    def test_semantic_annotations(self):
        """Test full semantic annotations."""
        annotations = SemanticMapper.get_semantic_annotations("temperature")
        assert "@type" in annotations
        assert annotations["@type"] == "saref:TemperatureSensor"
        assert "saref:measuresProperty" in annotations
        assert "sosa:observes" in annotations


class TestOntologyLoader:
    """Test ontology context loading."""

    def test_get_context(self):
        """Test getting full context."""
        context = OntologyLoader.get_context()
        assert isinstance(context, list)
        assert len(context) == 2
        assert context[0] == "https://www.w3.org/2022/wot/td/v1.1"
        assert isinstance(context[1], dict)

    def test_ontology_prefixes(self):
        """Test ontology prefix mappings."""
        prefixes = OntologyLoader.get_ontology_prefixes()
        assert "saref" in prefixes
        assert "sosa" in prefixes
        assert "qudt" in prefixes
        assert "opcua" in prefixes
        assert "unit" in prefixes

    def test_saref_prefix(self):
        """Test SAREF prefix URI."""
        prefixes = OntologyLoader.get_ontology_prefixes()
        assert prefixes["saref"] == "https://saref.etsi.org/core/"

    def test_expand_curie(self):
        """Test CURIE expansion."""
        full_uri = OntologyLoader.expand_curie("saref:TemperatureSensor")
        assert full_uri == "https://saref.etsi.org/core/TemperatureSensor"

    def test_expand_qudt_curie(self):
        """Test QUDT unit CURIE expansion."""
        full_uri = OntologyLoader.expand_curie("unit:DEG_C")
        assert full_uri == "http://qudt.org/vocab/unit/DEG_C"

    def test_expand_non_curie(self):
        """Test that non-CURIEs are returned unchanged."""
        uri = "http://example.com/full-uri"
        result = OntologyLoader.expand_curie(uri)
        assert result == uri

    def test_saref_terms_list(self):
        """Test SAREF terms list."""
        terms = OntologyLoader.get_saref_terms()
        assert isinstance(terms, list)
        assert len(terms) > 0
        assert "saref:TemperatureSensor" in terms
        assert "saref:PressureSensor" in terms

    def test_sosa_terms_list(self):
        """Test SOSA/SSN terms list."""
        terms = OntologyLoader.get_sosa_terms()
        assert isinstance(terms, list)
        assert "sosa:Sensor" in terms
        assert "sosa:observes" in terms


class MockSimulatorManager:
    """Mock simulator manager for testing."""

    def __init__(self):
        self.sensors = {}

    def add_mock_sensor(self, industry: str, sensor_info: Dict[str, Any]):
        """Add a mock sensor."""
        if industry not in self.sensors:
            self.sensors[industry] = []

        class MockConfig:
            def __init__(self, info):
                self.name = info["name"]
                self.sensor_type = type('obj', (object,), {'value': info["sensor_type"]})()
                self.unit = info["unit"]
                self.min_value = info.get("min_value", 0)
                self.max_value = info.get("max_value", 100)
                self.nominal_value = info.get("nominal_value", 50)

        class MockSimulator:
            def __init__(self, config):
                self.config = config

        self.sensors[industry].append(MockSimulator(MockConfig(sensor_info)))


class TestThingDescriptionGenerator:
    """Test Thing Description generation."""

    @pytest.fixture
    def mock_simulator(self):
        """Create mock simulator manager."""
        sim = MockSimulatorManager()
        sim.add_mock_sensor("mining", {
            "name": "crusher_1_motor_power",
            "sensor_type": "power",
            "unit": "kW",
            "min_value": 200,
            "max_value": 800,
            "nominal_value": 450
        })
        sim.add_mock_sensor("utilities", {
            "name": "turbine_1_bearing_temp",
            "sensor_type": "temperature",
            "unit": "°C",
            "min_value": 50,
            "max_value": 105,
            "nominal_value": 75
        })
        return sim

    @pytest.mark.asyncio
    async def test_td_generation_structure(self, mock_simulator):
        """Test Thing Description has correct structure."""
        td_gen = ThingDescriptionGenerator(
            mock_simulator,
            base_url="opc.tcp://localhost:4840",
            namespace_uri="http://example.com"
        )

        td = await td_gen.generate_td()

        # Check required fields
        assert "@context" in td
        assert "@type" in td
        assert td["@type"] == "Thing"
        assert "id" in td
        assert "title" in td
        assert "description" in td
        assert "base" in td
        assert "security" in td
        assert "securityDefinitions" in td
        assert "properties" in td

    @pytest.mark.asyncio
    async def test_td_context(self, mock_simulator):
        """Test Thing Description @context."""
        td_gen = ThingDescriptionGenerator(
            mock_simulator,
            base_url="opc.tcp://localhost:4840"
        )

        td = await td_gen.generate_td()

        assert isinstance(td["@context"], list)
        assert len(td["@context"]) == 2
        assert td["@context"][0] == "https://www.w3.org/2022/wot/td/v1.1"
        assert isinstance(td["@context"][1], dict)
        assert "saref" in td["@context"][1]

    @pytest.mark.asyncio
    async def test_td_properties(self, mock_simulator):
        """Test Thing Description properties."""
        td_gen = ThingDescriptionGenerator(
            mock_simulator,
            base_url="opc.tcp://localhost:4840"
        )

        td = await td_gen.generate_td()

        assert "properties" in td
        assert len(td["properties"]) >= 2  # At least our 2 mock sensors

    @pytest.mark.asyncio
    async def test_property_structure(self, mock_simulator):
        """Test property definition structure."""
        td_gen = ThingDescriptionGenerator(
            mock_simulator,
            base_url="opc.tcp://localhost:4840"
        )

        td = await td_gen.generate_td()

        # Check first property
        props = td["properties"]
        assert len(props) > 0

        # Get first property
        first_prop = next(iter(props.values()))

        # Check property fields
        assert "@type" in first_prop
        assert "title" in first_prop
        assert "type" in first_prop
        assert "forms" in first_prop
        assert len(first_prop["forms"]) > 0

    @pytest.mark.asyncio
    async def test_property_forms_opcua(self, mock_simulator):
        """Test property forms have OPC UA bindings."""
        td_gen = ThingDescriptionGenerator(
            mock_simulator,
            base_url="opc.tcp://localhost:4840"
        )

        td = await td_gen.generate_td()

        # Check first property form
        first_prop = next(iter(td["properties"].values()))
        form = first_prop["forms"][0]

        assert "href" in form
        assert "opcua:nodeId" in form
        assert "op" in form
        assert "subprotocol" in form
        assert form["subprotocol"] == "opcua"

    @pytest.mark.asyncio
    async def test_compact_td(self, mock_simulator):
        """Test compact Thing Description generation."""
        td_gen = ThingDescriptionGenerator(
            mock_simulator,
            base_url="opc.tcp://localhost:4840"
        )

        full_td = await td_gen.generate_td()
        compact_td = td_gen.generate_compact_td(full_td)

        # Compact should have summary fields
        assert "id" in compact_td
        assert "title" in compact_td
        assert "propertyCount" in compact_td
        assert compact_td["propertyCount"] == len(full_td["properties"])

    @pytest.mark.asyncio
    async def test_security_definitions(self, mock_simulator):
        """Test security definitions."""
        td_gen = ThingDescriptionGenerator(
            mock_simulator,
            base_url="opc.tcp://localhost:4840"
        )

        td = await td_gen.generate_td()

        assert "securityDefinitions" in td
        assert "nosec" in td["securityDefinitions"]
        assert td["security"] == ["nosec"]


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
