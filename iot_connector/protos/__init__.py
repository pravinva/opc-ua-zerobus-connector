"""
Protobuf schemas for IoT data ingestion to Databricks Unity Catalog.

This package contains compiled protobuf schemas for:
- MQTT sensor data (mqtt_bronze_pb2)
- Modbus register data (modbus_bronze_pb2)
- OPC-UA node data (opcua_bronze_pb2)

All schemas match the Unity Catalog table definitions in UNITY_CATALOG_SCHEMAS.md
"""

from protos import mqtt_bronze_pb2
from protos import modbus_bronze_pb2
from protos import opcua_bronze_pb2

__all__ = [
    "mqtt_bronze_pb2",
    "modbus_bronze_pb2",
    "opcua_bronze_pb2",
]
