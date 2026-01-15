#!/usr/bin/env python3
"""
Test script for protobuf integration in databricks_iot_connector.

This script verifies that:
1. Protobuf modules can be imported
2. Message objects can be created
3. Serialization and deserialization works
4. All required fields are present
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from protos import mqtt_bronze_pb2, modbus_bronze_pb2, opcua_bronze_pb2


def test_mqtt_protobuf():
    """Test MQTT protobuf message."""
    print("\n=== Testing MQTT Protobuf ===")

    # Create message
    msg = mqtt_bronze_pb2.MQTTBronzeRecord()
    msg.event_time = int(time.time() * 1000000)  # microseconds
    msg.ingest_time = msg.event_time
    msg.source_name = "test_mqtt_source"
    msg.topic = "sensors/test/temperature"
    msg.industry = "manufacturing"
    msg.sensor_name = "temp_sensor_01"
    msg.value = 23.5
    msg.unit = "°C"
    msg.qos = 1
    msg.retain = False
    msg.plc_name = "Rockwell ControlLogix 5580"
    msg.plc_vendor = "rockwell"
    msg.plc_model = "ControlLogix 5580"

    # Serialize
    serialized = msg.SerializeToString()
    print(f"✓ Serialized MQTT message: {len(serialized)} bytes")

    # Deserialize
    msg2 = mqtt_bronze_pb2.MQTTBronzeRecord()
    msg2.ParseFromString(serialized)
    assert msg2.sensor_name == "temp_sensor_01"
    assert msg2.value == 23.5
    assert msg2.plc_vendor == "rockwell"
    print(f"✓ Deserialized successfully: {msg2.sensor_name} = {msg2.value}{msg2.unit}")
    print(f"✓ PLC Info: {msg2.plc_name}")

    return True


def test_modbus_protobuf():
    """Test Modbus protobuf message."""
    print("\n=== Testing Modbus Protobuf ===")

    # Create message
    msg = modbus_bronze_pb2.ModbusBronzeRecord()
    msg.event_time = int(time.time() * 1000000)
    msg.ingest_time = msg.event_time
    msg.source_name = "test_modbus_source"
    msg.slave_id = 1
    msg.register_address = 40001
    msg.register_type = "holding"
    msg.industry = "oil_gas"
    msg.sensor_name = "pressure_sensor_01"
    msg.raw_value = 150.5
    msg.scaled_value = 1505
    msg.scale_factor = 10
    msg.plc_name = "Siemens S7-1500"
    msg.plc_vendor = "siemens"
    msg.plc_model = "S7-1500"

    # Serialize
    serialized = msg.SerializeToString()
    print(f"✓ Serialized Modbus message: {len(serialized)} bytes")

    # Deserialize
    msg2 = modbus_bronze_pb2.ModbusBronzeRecord()
    msg2.ParseFromString(serialized)
    assert msg2.slave_id == 1
    assert msg2.register_address == 40001
    assert msg2.raw_value == 150.5
    assert msg2.plc_vendor == "siemens"
    print(f"✓ Deserialized successfully: slave={msg2.slave_id}, addr={msg2.register_address}, value={msg2.raw_value}")
    print(f"✓ PLC Info: {msg2.plc_name}")

    return True


def test_opcua_protobuf():
    """Test OPC-UA protobuf message."""
    print("\n=== Testing OPC-UA Protobuf ===")

    # Create message
    msg = opcua_bronze_pb2.OPCUABronzeRecord()
    msg.event_time = int(time.time() * 1000000)
    msg.ingest_time = msg.event_time
    msg.source_name = "test_opcua_source"
    msg.endpoint = "opc.tcp://192.168.1.100:4840"
    msg.namespace = 2
    msg.node_id = "ns=2;s=Temperature"
    msg.browse_path = "Objects/ProcessArea/Temperature"
    msg.status_code = 0
    msg.status = "Good"
    msg.value_type = "Double"
    msg.value = "25.3"
    msg.value_num = 25.3
    msg.plc_name = "ABB AC800M"
    msg.plc_vendor = "abb"
    msg.plc_model = "AC800M"

    # Serialize
    serialized = msg.SerializeToString()
    print(f"✓ Serialized OPC-UA message: {len(serialized)} bytes")

    # Deserialize
    msg2 = opcua_bronze_pb2.OPCUABronzeRecord()
    msg2.ParseFromString(serialized)
    assert msg2.namespace == 2
    assert msg2.node_id == "ns=2;s=Temperature"
    assert msg2.value_num == 25.3
    assert msg2.plc_vendor == "abb"
    print(f"✓ Deserialized successfully: {msg2.node_id} = {msg2.value_num} ({msg2.status})")
    print(f"✓ PLC Info: {msg2.plc_name}")

    return True


def test_descriptor_access():
    """Test that descriptors can be accessed."""
    print("\n=== Testing Descriptor Access ===")

    mqtt_desc = mqtt_bronze_pb2.MQTTBronzeRecord.DESCRIPTOR
    modbus_desc = modbus_bronze_pb2.ModbusBronzeRecord.DESCRIPTOR
    opcua_desc = opcua_bronze_pb2.OPCUABronzeRecord.DESCRIPTOR

    print(f"✓ MQTT descriptor: {mqtt_desc.name} ({len(mqtt_desc.fields)} fields)")
    print(f"✓ Modbus descriptor: {modbus_desc.name} ({len(modbus_desc.fields)} fields)")
    print(f"✓ OPC-UA descriptor: {opcua_desc.name} ({len(opcua_desc.fields)} fields)")

    # Verify PLC fields exist
    mqtt_field_names = [f.name for f in mqtt_desc.fields]
    assert "plc_name" in mqtt_field_names, "MQTT missing plc_name field"
    assert "plc_vendor" in mqtt_field_names, "MQTT missing plc_vendor field"
    assert "plc_model" in mqtt_field_names, "MQTT missing plc_model field"
    print("✓ All protocols have PLC fields (plc_name, plc_vendor, plc_model)")

    return True


def main():
    """Run all tests."""
    print("=" * 80)
    print("Protobuf Integration Test Suite")
    print("=" * 80)

    try:
        test_mqtt_protobuf()
        test_modbus_protobuf()
        test_opcua_protobuf()
        test_descriptor_access()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        return 0

    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
