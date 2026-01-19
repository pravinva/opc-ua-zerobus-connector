"""
Databricks IoT Connector for DMZ Deployment

Production-ready standalone connector for streaming industrial IoT data
from OPC-UA, MQTT, and Modbus sources to Databricks Unity Catalog via ZeroBus SDK.
"""

__version__ = "1.0.0"
__author__ = "Databricks"

from connector.config_loader import ConfigLoader
from connector.zerobus_client import ZeroBusClient
from connector.backpressure import BackpressureManager

__all__ = [
    "ConfigLoader",
    "ZeroBusClient",
    "BackpressureManager",
]
