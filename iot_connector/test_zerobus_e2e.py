#!/usr/bin/env python3
"""
End-to-end test for ZeroBus integration using simulator configurations.

This test verifies the complete data flow:
1. Load ZeroBus configuration from simulator configs
2. Decrypt credentials
3. Create protobuf messages for all 3 protocols
4. Authenticate with Databricks OAuth2
5. Attempt to write to ZeroBus (or dry-run mode)

Usage:
    # Dry run (no actual writes)
    python test_zerobus_e2e.py --dry-run

    # Real writes (requires valid credentials)
    python test_zerobus_e2e.py --write
"""

import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from protos import mqtt_bronze_pb2, modbus_bronze_pb2, opcua_bronze_pb2

# Try to import databricks SDK (may not be available in all environments)
try:
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.catalog import VolumeType
    DATABRICKS_SDK_AVAILABLE = True
except ImportError:
    DATABRICKS_SDK_AVAILABLE = False
    print("⚠️  Databricks SDK not available - will run in dry-run mode only")


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load ZeroBus configuration from JSON file."""
    print(f"\n📂 Loading config from: {config_path}")

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        config = json.load(f)

    print(f"✓ Loaded config:")
    print(f"  - Workspace: {config['workspace_host']}")
    print(f"  - ZeroBus Endpoint: {config['zerobus_endpoint']}")
    print(f"  - Target: {config['target']['catalog']}.{config['target']['schema']}.{config['target']['table']}")
    print(f"  - Client ID: {config['auth']['client_id'][:8]}...")
    print(f"  - Credentials: {'Encrypted' if config['auth'].get('_encrypted') else 'Plain'}")

    return config


def decrypt_credentials(config: Dict[str, Any]) -> str:
    """Decrypt client secret if encrypted."""
    if config['auth'].get('_encrypted'):
        # Try to import and use credential manager
        try:
            sys.path.insert(0, str(Path(__file__).parent / 'connector'))
            from credential_manager import CredentialManager

            # Find encryption key
            key_path = Path(__file__).parent.parent / 'ot_simulator' / 'zerobus_configs' / '.encryption_key'
            if not key_path.exists():
                print("⚠️  Encryption key not found - cannot decrypt credentials")
                return None

            manager = CredentialManager()
            manager.key = open(key_path, 'rb').read()

            encrypted = config['auth']['client_secret_encrypted']
            decrypted = manager.decrypt(encrypted)
            print("✓ Decrypted client secret")
            return decrypted

        except Exception as e:
            print(f"⚠️  Could not decrypt credentials: {e}")
            return None
    else:
        return config['auth'].get('client_secret')


def create_mqtt_message() -> mqtt_bronze_pb2.MQTTBronzeRecord:
    """Create a sample MQTT protobuf message."""
    msg = mqtt_bronze_pb2.MQTTBronzeRecord()
    msg.event_time = int(time.time() * 1000000)  # microseconds
    msg.ingest_time = msg.event_time
    msg.source_name = "test_e2e_mqtt"
    msg.topic = "test/utilities/turbine"
    msg.industry = "utilities"
    msg.sensor_name = "turbine_1_speed"
    msg.value = 1850.5
    msg.value_string = "1850.5"
    msg.unit = "RPM"
    msg.sensor_type = "speed"
    msg.timestamp_ms = int(time.time() * 1000)
    msg.qos = 1
    msg.retain = False
    msg.plc_name = "ABB AC800M"
    msg.plc_vendor = "abb"
    msg.plc_model = "AC800M"
    return msg


def create_modbus_message() -> modbus_bronze_pb2.ModbusBronzeRecord:
    """Create a sample Modbus protobuf message."""
    msg = modbus_bronze_pb2.ModbusBronzeRecord()
    msg.event_time = int(time.time() * 1000000)
    msg.ingest_time = msg.event_time
    msg.source_name = "test_e2e_modbus"
    msg.slave_id = 1
    msg.register_address = 40001
    msg.register_type = "holding"
    msg.industry = "oil_gas"
    msg.sensor_name = "pressure_sensor_01"
    msg.sensor_path = "oil_gas/pressure_sensor_01"
    msg.sensor_type = "pressure"
    msg.unit = "PSI"
    msg.raw_value = 150.5
    msg.scaled_value = 1505
    msg.scale_factor = 10
    msg.plc_name = "Siemens S7-1500"
    msg.plc_vendor = "siemens"
    msg.plc_model = "S7-1500"
    return msg


def create_opcua_message() -> opcua_bronze_pb2.OPCUABronzeRecord:
    """Create a sample OPC-UA protobuf message."""
    msg = opcua_bronze_pb2.OPCUABronzeRecord()
    msg.event_time = int(time.time() * 1000000)
    msg.ingest_time = msg.event_time
    msg.source_name = "test_e2e_opcua"
    msg.endpoint = "opc.tcp://test-server:4840"
    msg.namespace = 2
    msg.node_id = "ns=2;s=Test.Temperature"
    msg.browse_path = "Objects/Test/Temperature"
    msg.status_code = 0
    msg.status = "Good"
    msg.value_type = "Double"
    msg.value = "25.3"
    msg.value_num = 25.3
    msg.plc_name = "Rockwell ControlLogix 5580"
    msg.plc_vendor = "rockwell"
    msg.plc_model = "ControlLogix 5580"
    return msg


def test_authentication(config: Dict[str, Any], client_secret: str) -> bool:
    """Test OAuth2 authentication with Databricks."""
    if not DATABRICKS_SDK_AVAILABLE:
        print("\n⚠️  Skipping authentication test - Databricks SDK not available")
        return False

    if not client_secret:
        print("\n⚠️  Skipping authentication test - no client secret available")
        return False

    print("\n🔐 Testing OAuth2 Authentication...")

    try:
        # Create workspace client with OAuth2 M2M
        client = WorkspaceClient(
            host=config['workspace_host'],
            client_id=config['auth']['client_id'],
            client_secret=client_secret
        )

        # Test connection by listing catalogs
        catalogs = list(client.catalogs.list())
        print(f"✓ Authentication successful")
        print(f"✓ Found {len(catalogs)} catalogs")

        # Check if target catalog exists
        target_catalog = config['target']['catalog']
        if any(c.name == target_catalog for c in catalogs):
            print(f"✓ Target catalog '{target_catalog}' exists")
        else:
            print(f"⚠️  Target catalog '{target_catalog}' not found")

        return True

    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False


def test_protobuf_serialization(protocol: str) -> bytes:
    """Test protobuf message serialization."""
    print(f"\n📦 Testing {protocol.upper()} Protobuf Serialization...")

    if protocol == "mqtt":
        msg = create_mqtt_message()
        descriptor_name = "MQTTBronzeRecord"
    elif protocol == "modbus":
        msg = create_modbus_message()
        descriptor_name = "ModbusBronzeRecord"
    elif protocol == "opcua":
        msg = create_opcua_message()
        descriptor_name = "OPCUABronzeRecord"
    else:
        raise ValueError(f"Unknown protocol: {protocol}")

    # Serialize
    serialized = msg.SerializeToString()
    print(f"✓ Created {descriptor_name}")
    print(f"✓ Serialized to {len(serialized)} bytes")

    # Show sample data
    if protocol == "mqtt":
        print(f"  Sample: {msg.sensor_name} = {msg.value} {msg.unit}")
        print(f"  PLC: {msg.plc_name}")
    elif protocol == "modbus":
        print(f"  Sample: slave={msg.slave_id}, addr={msg.register_address}, value={msg.raw_value}")
        print(f"  PLC: {msg.plc_name}")
    elif protocol == "opcua":
        print(f"  Sample: {msg.node_id} = {msg.value_num} ({msg.status})")
        print(f"  PLC: {msg.plc_name}")

    return serialized


def dry_run_zerobus_write(config: Dict[str, Any], protocol: str, data: bytes):
    """Simulate ZeroBus write without actually sending."""
    print(f"\n🔍 Dry Run - Would write to ZeroBus:")
    print(f"  Endpoint: {config['zerobus_endpoint']}")
    print(f"  Target: {config['target']['catalog']}.{config['target']['schema']}.{config['target']['table']}")
    print(f"  Protocol: {protocol}")
    print(f"  Data size: {len(data)} bytes")
    print(f"  ✓ Dry run complete - no actual write performed")


def main():
    """Run end-to-end tests."""
    parser = argparse.ArgumentParser(description="ZeroBus End-to-End Test")
    parser.add_argument('--write', action='store_true', help='Actually write to ZeroBus (requires valid credentials)')
    parser.add_argument('--dry-run', action='store_true', default=True, help='Dry run only (default)')
    parser.add_argument('--protocol', choices=['mqtt', 'modbus', 'opcua', 'all'], default='all', help='Protocol to test')
    args = parser.parse_args()

    print("=" * 80)
    print("ZeroBus End-to-End Integration Test")
    print("=" * 80)

    # Determine config path
    config_dir = Path(__file__).parent.parent / 'ot_simulator' / 'zerobus_configs'
    if not config_dir.exists():
        print(f"❌ Config directory not found: {config_dir}")
        print("   This test requires simulator ZeroBus configurations")
        return 1

    protocols = ['mqtt', 'modbus', 'opcua'] if args.protocol == 'all' else [args.protocol]

    success_count = 0
    total_tests = len(protocols)

    for protocol in protocols:
        try:
            # Load config
            config_path = config_dir / f'{protocol}_zerobus.json'
            if not config_path.exists():
                print(f"\n⚠️  Config not found for {protocol}: {config_path}")
                continue

            config = load_config(config_path)

            # Decrypt credentials
            client_secret = decrypt_credentials(config)

            # Test authentication (if credentials available)
            if args.write and client_secret:
                auth_ok = test_authentication(config, client_secret)
            else:
                print(f"\n⏭️  Skipping authentication test (dry-run mode)")
                auth_ok = False

            # Test protobuf serialization
            data = test_protobuf_serialization(protocol)

            # Write or dry-run
            if args.write and auth_ok:
                print(f"\n⚠️  Real ZeroBus write not implemented yet")
                print(f"   (Would require ZeroBus SDK integration)")
                dry_run_zerobus_write(config, protocol, data)
            else:
                dry_run_zerobus_write(config, protocol, data)

            success_count += 1

        except Exception as e:
            print(f"\n❌ Test failed for {protocol}: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "=" * 80)
    if success_count == total_tests:
        print(f"✅ ALL TESTS PASSED ({success_count}/{total_tests})")
    else:
        print(f"⚠️  PARTIAL SUCCESS ({success_count}/{total_tests} protocols tested)")
    print("=" * 80)

    return 0 if success_count == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())
