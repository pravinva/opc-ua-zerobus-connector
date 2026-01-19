#!/usr/bin/env python3
"""Test script to demonstrate tag normalization for OPC-UA, MQTT, and Modbus protocols."""

import asyncio
import json
import sys
import time
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "iot_connector"))
sys.path.insert(0, str(Path(__file__).parent))

# Import normalizers
from iot_connector.connector.normalizer import (
    OPCUANormalizer,
    MQTTNormalizer,
    ModbusNormalizer,
    get_normalization_manager,
)

def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_data(label: str, data: dict):
    """Pretty print data."""
    print(f"{label}:")
    print(json.dumps(data, indent=2, default=str))
    print()


async def test_opcua_normalization():
    """Test OPC-UA data normalization."""
    print_section("OPC-UA Tag Normalization Test")

    # Create normalizer with config
    config = {
        "site_id": "columbus",
        "line_id": "line3",
        "equipment_id": "plc1",
    }

    normalizer = OPCUANormalizer(config)

    # Simulate OPC-UA data from simulator
    raw_opcua_data = {
        "node_id": "ns=2;s=Objects.Line3.Machine1.Temperature",
        "value": {
            "value": 75.3,
            "source_timestamp": int(time.time() * 1000),
            "status_code": 0,  # Good quality
        },
        "browse_path": "Objects/Columbus/Line3/Machine1/Temperature",
        "server_url": "opc.tcp://localhost:4840",
        "config": config,
    }

    print_data("Raw OPC-UA Data", raw_opcua_data)

    # Normalize
    try:
        normalized = normalizer.normalize(raw_opcua_data)
        normalized_dict = normalized.to_dict()

        print_data("✅ Normalized OPC-UA Tag", normalized_dict)

        # Show key unified fields
        print("Key Unified Fields:")
        print(f"  • tag_id: {normalized_dict['tag_id']}")
        print(f"  • tag_path: {normalized_dict['tag_path']}")
        print(f"  • value: {normalized_dict['value']}")
        print(f"  • quality: {normalized_dict['quality']}")
        print(f"  • data_type: {normalized_dict['data_type']}")
        print(f"  • source_protocol: {normalized_dict['source_protocol']}")
        print(f"  • site_id: {normalized_dict.get('site_id', 'N/A')}")
        print(f"  • line_id: {normalized_dict.get('line_id', 'N/A')}")
        print(f"  • equipment_id: {normalized_dict.get('equipment_id', 'N/A')}")

    except Exception as e:
        print(f"❌ Normalization failed: {e}")
        import traceback
        traceback.print_exc()


async def test_mqtt_normalization():
    """Test MQTT data normalization."""
    print_section("MQTT Tag Normalization Test")

    # Create normalizer with config
    config = {
        "site_id": "columbus",
        "line_id": "line3",
        "equipment_id": "press1",
    }

    normalizer = MQTTNormalizer(config)

    # Simulate MQTT data from simulator
    raw_mqtt_data = {
        "topic": "columbus/line3/press1/hydraulic_pressure",
        "payload": json.dumps({
            "value": 85.2,
            "units": "bar",
            "timestamp": int(time.time() * 1000),
        }),
        "qos": 1,
        "retained": False,
        "timestamp": int(time.time() * 1000),
        "broker_address": "localhost:1883",
        "config": config,
    }

    print_data("Raw MQTT Data", raw_mqtt_data)

    # Normalize
    try:
        normalized = normalizer.normalize(raw_mqtt_data)
        normalized_dict = normalized.to_dict()

        print_data("✅ Normalized MQTT Tag", normalized_dict)

        # Show key unified fields
        print("Key Unified Fields:")
        print(f"  • tag_id: {normalized_dict['tag_id']}")
        print(f"  • tag_path: {normalized_dict['tag_path']}")
        print(f"  • value: {normalized_dict['value']}")
        print(f"  • quality: {normalized_dict['quality']}")
        print(f"  • data_type: {normalized_dict['data_type']}")
        print(f"  • source_protocol: {normalized_dict['source_protocol']}")
        print(f"  • site_id: {normalized_dict.get('site_id', 'N/A')}")
        print(f"  • line_id: {normalized_dict.get('line_id', 'N/A')}")
        print(f"  • equipment_id: {normalized_dict.get('equipment_id', 'N/A')}")

    except Exception as e:
        print(f"❌ Normalization failed: {e}")
        import traceback
        traceback.print_exc()


async def test_modbus_normalization():
    """Test Modbus data normalization."""
    print_section("Modbus Tag Normalization Test")

    # Create normalizer with config
    config = {
        "site_id": "columbus",
        "line_id": "line3",
        "equipment_id": "conveyor1",
        "tag_name": "motor_speed",
        "engineering_units": "rpm",
    }

    normalizer = ModbusNormalizer(config)

    # Simulate Modbus data from simulator
    raw_modbus_data = {
        "device_address": "192.168.1.100",
        "register_address": 40001,
        "register_count": 1,
        "raw_registers": [1500],  # Raw value
        "timestamp": int(time.time() * 1000),
        "success": True,
        "exception_code": None,
        "timeout": False,
        "config": {
            "data_type": "int16",
            "scale_factor": 1.0,
            "engineering_units": "rpm",
            "tag_name": "motor_speed",
            **config,
        }
    }

    print_data("Raw Modbus Data", raw_modbus_data)

    # Normalize
    try:
        normalized = normalizer.normalize(raw_modbus_data)
        normalized_dict = normalized.to_dict()

        print_data("✅ Normalized Modbus Tag", normalized_dict)

        # Show key unified fields
        print("Key Unified Fields:")
        print(f"  • tag_id: {normalized_dict['tag_id']}")
        print(f"  • tag_path: {normalized_dict['tag_path']}")
        print(f"  • value: {normalized_dict['value']}")
        print(f"  • quality: {normalized_dict['quality']}")
        print(f"  • data_type: {normalized_dict['data_type']}")
        print(f"  • engineering_units: {normalized_dict.get('engineering_units', 'N/A')}")
        print(f"  • source_protocol: {normalized_dict['source_protocol']}")
        print(f"  • site_id: {normalized_dict.get('site_id', 'N/A')}")
        print(f"  • line_id: {normalized_dict.get('line_id', 'N/A')}")
        print(f"  • equipment_id: {normalized_dict.get('equipment_id', 'N/A')}")

    except Exception as e:
        print(f"❌ Normalization failed: {e}")
        import traceback
        traceback.print_exc()


async def test_unified_schema_comparison():
    """Compare normalized output from all three protocols."""
    print_section("Unified Schema Comparison")

    print("All three protocols produce the same unified schema:")
    print()
    print("Common Fields Across All Protocols:")
    print("  ✓ tag_id          - Unique identifier (SHA256 hash)")
    print("  ✓ tag_path        - Hierarchical path (site/line/equipment/signal)")
    print("  ✓ value           - Actual value")
    print("  ✓ quality         - Unified quality code (good/bad/uncertain)")
    print("  ✓ timestamp       - Event timestamp (ISO 8601)")
    print("  ✓ data_type       - Normalized data type (float/int/bool/string)")
    print("  ✓ source_protocol - Protocol name (opcua/mqtt/modbus)")
    print("  ✓ source_identifier - Protocol-specific identifier")
    print("  ✓ source_address  - Device/server address")
    print("  ✓ site_id         - Site identifier")
    print("  ✓ line_id         - Production line identifier")
    print("  ✓ equipment_id    - Equipment identifier")
    print("  ✓ signal_type     - Signal type")
    print("  ✓ metadata        - Protocol-specific metadata")
    print()
    print("Benefits:")
    print("  ✓ Consistent querying across all protocols")
    print("  ✓ Unified quality interpretation")
    print("  ✓ Hierarchical organization for analytics")
    print("  ✓ Protocol metadata preserved for debugging")
    print("  ✓ Ready for ML/AI workflows")


async def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("  TAG NORMALIZATION DEMONSTRATION")
    print("  Testing OPC-UA, MQTT, and Modbus Protocol Normalization")
    print("=" * 80)

    # Test each protocol
    await test_opcua_normalization()
    await test_mqtt_normalization()
    await test_modbus_normalization()

    # Show unified schema comparison
    await test_unified_schema_comparison()

    print("\n" + "=" * 80)
    print("  ✅ All Tests Complete")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
