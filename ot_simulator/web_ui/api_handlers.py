"""API route handlers for the web UI.

This module contains all HTTP endpoint handlers except the main index page.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from aiohttp import web

from ot_simulator.sensor_models import IndustryType, get_industry_sensors
from ot_simulator.credential_manager import CredentialManager

# Import protobuf descriptors for all protocols
from ot_simulator.opcua_bronze_pb2 import OPCUABronzeRecord
from ot_simulator.mqtt_bronze_pb2 import MQTTBronzeRecord
from ot_simulator.modbus_bronze_pb2 import ModbusBronzeRecord

if TYPE_CHECKING:
    from ot_simulator.simulator_manager import SimulatorManager

logger = logging.getLogger("ot_simulator.api_handlers")


def get_protobuf_descriptor(protocol: str):
    """Get the protobuf descriptor for the given protocol.

    Args:
        protocol: Protocol name ('mqtt', 'opcua', 'modbus')

    Returns:
        Protobuf descriptor for the protocol

    Raises:
        ValueError: If protocol is not recognized
    """
    protocol_lower = protocol.lower()
    if protocol_lower == "mqtt":
        return MQTTBronzeRecord.DESCRIPTOR
    elif protocol_lower == "opcua":
        return OPCUABronzeRecord.DESCRIPTOR
    elif protocol_lower == "modbus":
        return ModbusBronzeRecord.DESCRIPTOR
    else:
        raise ValueError(f"Unknown protocol: {protocol}")


def dict_to_protobuf(protocol: str, data: dict[str, Any]):
    """Convert a dictionary to a protobuf message for the given protocol.

    Args:
        protocol: Protocol name ('mqtt', 'opcua', 'modbus')
        data: Dictionary containing record data

    Returns:
        Protobuf message object

    Raises:
        ValueError: If protocol is not recognized
    """
    protocol_lower = protocol.lower()

    if protocol_lower == "mqtt":
        msg = MQTTBronzeRecord()
        msg.event_time = data.get("event_time", 0)
        msg.ingest_time = data.get("ingest_time", 0)
        msg.source_name = data.get("source_name", "")
        msg.topic = data.get("topic", "")
        msg.industry = data.get("industry", "")
        msg.sensor_name = data.get("sensor_name", "")
        msg.value = data.get("value", 0.0)
        msg.value_string = data.get("value_string", "")
        msg.unit = data.get("unit", "")
        msg.sensor_type = data.get("sensor_type", "")
        msg.timestamp_ms = data.get("timestamp_ms", 0)
        msg.qos = data.get("qos", 0)
        msg.retain = data.get("retain", False)
        msg.plc_name = data.get("plc_name", "")
        msg.plc_vendor = data.get("plc_vendor", "")
        msg.plc_model = data.get("plc_model", "")
        return msg

    elif protocol_lower == "opcua":
        msg = OPCUABronzeRecord()
        msg.event_time = data.get("event_time", 0)
        msg.ingest_time = data.get("ingest_time", 0)
        msg.source_name = data.get("source_name", "")
        msg.endpoint = data.get("endpoint", "")
        msg.namespace = data.get("namespace", 0)
        msg.node_id = data.get("node_id", "")
        msg.browse_path = data.get("browse_path", "")
        msg.status_code = data.get("status_code") or 0
        msg.status = data.get("status", "")
        msg.value_type = data.get("value_type", "")
        msg.value = data.get("value", "")
        msg.value_num = data.get("value_num") or 0.0
        if data.get("raw"):
            msg.raw = data["raw"]
        msg.plc_name = data.get("plc_name", "")
        msg.plc_vendor = data.get("plc_vendor", "")
        msg.plc_model = data.get("plc_model", "")
        return msg

    elif protocol_lower == "modbus":
        msg = ModbusBronzeRecord()
        msg.event_time = data.get("event_time", 0)
        msg.ingest_time = data.get("ingest_time", 0)
        msg.source_name = data.get("source_name", "")
        msg.slave_id = data.get("slave_id", 0)
        msg.register_address = data.get("register_address", 0)
        msg.register_type = data.get("register_type", "")
        msg.industry = data.get("industry", "")
        msg.sensor_name = data.get("sensor_name", "")
        msg.sensor_path = data.get("sensor_path", "")
        msg.sensor_type = data.get("sensor_type", "")
        msg.unit = data.get("unit", "")
        msg.raw_value = data.get("raw_value", 0.0)
        msg.scaled_value = data.get("scaled_value", 0)
        msg.scale_factor = data.get("scale_factor", 0)
        msg.plc_name = data.get("plc_name", "")
        msg.plc_vendor = data.get("plc_vendor", "")
        msg.plc_model = data.get("plc_model", "")
        return msg

    else:
        raise ValueError(f"Unknown protocol: {protocol}")


class APIHandlers:
    """Handles API routes for the web UI."""

    def __init__(self, config: Any, simulator_manager: SimulatorManager):
        """Initialize API handlers.

        Args:
            config: Simulator configuration
            simulator_manager: SimulatorManager instance
        """
        self.config = config
        self.manager = simulator_manager
        self.credential_manager = CredentialManager()

        # Zero-Bus streaming state per protocol
        self.streaming_tasks: dict[str, asyncio.Task] = {}
        self.streaming_active: dict[str, bool] = {}

    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({"status": "healthy"})

    async def handle_list_sensors(self, request: web.Request) -> web.Response:
        """List all available sensors grouped by industry."""
        industries = {}

        for industry in IndustryType:
            industry_sensors = get_industry_sensors(industry)
            sensors_list = []

            # Get PLC info for this industry (if available)
            plc_name = None
            plc_vendor = None
            plc_model = None
            if self.manager.plc_manager and self.manager.plc_manager.enabled:
                plc_name = self.manager.plc_manager.industry_to_plc.get(industry.value)
                if plc_name:
                    plc = self.manager.plc_manager.plcs.get(plc_name)
                    if plc:
                        plc_vendor = plc.config.vendor.value
                        plc_model = plc.config.model

            for sensor in industry_sensors:
                # Determine which protocols this sensor is available on
                # All sensors are available on all enabled protocols
                protocols = []
                if self.config.opcua.enabled and industry.value in self.config.opcua.industries:
                    protocols.append("opcua")
                if self.config.mqtt.enabled and industry.value in self.config.mqtt.industries:
                    protocols.append("mqtt")
                if self.config.modbus.enabled and industry.value in self.config.modbus.industries:
                    protocols.append("modbus")

                sensors_list.append({
                    "path": f"{industry.value}/{sensor.config.name}",
                    "name": sensor.config.name,
                    "industry": industry.value,
                    "min_value": sensor.config.min_value,
                    "max_value": sensor.config.max_value,
                    "unit": sensor.config.unit,
                    "type": sensor.config.sensor_type.value,
                    "protocols": protocols,
                    "plc_vendor": plc_vendor,
                    "plc_model": plc_model,
                })

            if sensors_list:  # Only include industries with sensors
                industries[industry.value] = {
                    "name": industry.value,
                    "display_name": industry.value.replace("_", " ").title(),
                    "sensor_count": len(sensors_list),
                    "sensors": sensors_list,
                    "plc_name": plc_name,
                    "plc_vendor": plc_vendor,
                    "plc_model": plc_model,
                }

        return web.json_response(industries)

    async def handle_list_industries(self, request: web.Request) -> web.Response:
        """List all available industries."""
        industries = [
            {"name": industry.value, "sensor_count": len(get_industry_sensors(industry))} for industry in IndustryType
        ]
        return web.json_response(industries)

    async def handle_zerobus_config_load(self, request: web.Request) -> web.Response:
        """Load Zero-Bus configuration for a protocol."""
        try:
            data = await request.json()
            protocol = data.get("protocol")

            if not protocol:
                return web.json_response({"success": False, "message": "Missing protocol"})

            # Load configuration (credentials will be decrypted)
            config = self.credential_manager.load_config(protocol)

            if config:
                # Send actual credentials to frontend (they're already decrypted by credential_manager)
                return web.json_response({
                    "success": True,
                    "config": config
                })
            else:
                return web.json_response({
                    "success": False,
                    "message": "No saved configuration found"
                })

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            return web.json_response({
                "success": False,
                "message": str(e),
                "detail": error_detail
            })

    async def handle_zerobus_start(self, request: web.Request) -> web.Response:
        """Start Zero-Bus streaming for a protocol."""
        try:
            data = await request.json()
            protocol = data.get("protocol")

            if not protocol:
                return web.json_response({"success": False, "message": "Missing protocol"})

            # Check if already streaming
            if self.streaming_active.get(protocol, False):
                return web.json_response({
                    "success": False,
                    "message": f"{protocol.upper()} streaming is already active"
                })

            # Load saved configuration
            config = self.credential_manager.load_config(protocol)
            if not config:
                return web.json_response({
                    "success": False,
                    "message": f"No saved configuration found for {protocol}. Please save configuration first."
                })

            # Validate required fields
            if not config.get("workspace_host") or not config.get("zerobus_endpoint"):
                return web.json_response({
                    "success": False,
                    "message": "Invalid configuration: missing workspace_host or zerobus_endpoint"
                })

            # Start streaming task
            task = asyncio.create_task(self._stream_to_zerobus(protocol, config))
            self.streaming_tasks[protocol] = task
            self.streaming_active[protocol] = True

            return web.json_response({
                "success": True,
                "message": f"{protocol.upper()} streaming started successfully"
            })

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"Error starting Zero-Bus stream: {error_detail}")
            return web.json_response({
                "success": False,
                "message": str(e),
                "detail": error_detail
            })

    async def handle_zerobus_stop(self, request: web.Request) -> web.Response:
        """Stop Zero-Bus streaming for a protocol."""
        try:
            data = await request.json()
            protocol = data.get("protocol")

            if not protocol:
                return web.json_response({"success": False, "message": "Missing protocol"})

            # Check if streaming is active
            if not self.streaming_active.get(protocol, False):
                return web.json_response({
                    "success": False,
                    "message": f"{protocol.upper()} streaming is not active"
                })

            # Cancel the task
            task = self.streaming_tasks.get(protocol)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            self.streaming_active[protocol] = False
            self.streaming_tasks.pop(protocol, None)

            return web.json_response({
                "success": True,
                "message": f"{protocol.upper()} streaming stopped successfully"
            })

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"Error stopping Zero-Bus stream: {error_detail}")
            return web.json_response({
                "success": False,
                "message": str(e),
                "detail": error_detail
            })

    async def handle_zerobus_status(self, request: web.Request) -> web.Response:
        """Get Zero-Bus streaming status for all protocols."""
        try:
            status = {}
            for protocol in ["opcua", "mqtt", "modbus"]:
                active = self.streaming_active.get(protocol, False)
                status[protocol] = {
                    "active": active,
                    "has_config": self.credential_manager.load_config(protocol) is not None
                }

            return web.json_response({
                "success": True,
                "status": status
            })

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"Error getting Zero-Bus status: {error_detail}")
            return web.json_response({
                "success": False,
                "message": str(e),
                "detail": error_detail
            })

    async def _stream_to_zerobus(self, protocol: str, config: dict[str, Any]):
        """Background task that streams sensor data to Zero-Bus."""
        from zerobus.sdk.aio import ZerobusSdk
        from zerobus.sdk.shared import TableProperties

        logger.info(f"Starting {protocol.upper()} to Zero-Bus streaming")

        # Get direct credentials from config
        auth = config.get("auth", {})
        client_id = auth.get("client_id", "").strip()
        client_secret = auth.get("client_secret", "").strip()

        if not client_id or not client_secret:
            logger.error(f"{protocol.upper()}: Missing OAuth credentials")
            self.streaming_active[protocol] = False
            return

        # Get connection details
        workspace_host = config.get("workspace_host", "").strip().rstrip("/")
        zerobus_endpoint = config.get("zerobus_endpoint", "").strip()
        target = config.get("target", {})

        catalog = target.get("catalog", "").strip()
        schema = target.get("schema", "").strip()
        table = target.get("table", "").strip()

        if not workspace_host or not zerobus_endpoint or not catalog or not schema or not table:
            logger.error(f"{protocol.upper()}: Invalid configuration")
            self.streaming_active[protocol] = False
            return

        table_name = f"{catalog}.{schema}.{table}"

        # Initialize SDK
        sdk = ZerobusSdk(zerobus_endpoint, workspace_host)

        # Get protobuf descriptor for this protocol
        descriptor = get_protobuf_descriptor(protocol)
        table_properties = TableProperties(table_name, descriptor_proto=descriptor)

        # Configure stream for protobuf record type
        from zerobus.sdk.shared import RecordType, StreamConfigurationOptions
        stream_options = StreamConfigurationOptions(
            record_type=RecordType.PROTO,
            max_inflight_records=1000,
            recovery=True,
            flush_timeout_ms=60000,
            server_lack_of_ack_timeout_ms=60000,
        )

        # Get protocol-specific data source from manager's simulators dict
        simulator = self.manager.simulators.get(protocol)
        if not simulator:
            logger.error(f"{protocol.upper()} simulator not available in manager")
            self.streaming_active[protocol] = False
            return

        # Stream data at configured interval (default 5 seconds)
        interval = config.get("streaming_interval_seconds", 5)
        record_count = 0

        # Get endpoint for OPC-UA
        opcua_endpoint = getattr(self.config, 'opcua', None)
        if opcua_endpoint and hasattr(opcua_endpoint, 'endpoint'):
            opcua_endpoint = opcua_endpoint.endpoint
        else:
            opcua_endpoint = "opc.tcp://0.0.0.0:4840/ot-simulator/server/"
        source_name = f"{protocol}_simulator"

        # Create stream once outside the loop
        stream = None
        try:
            stream = await sdk.create_stream(client_id, client_secret, table_properties, stream_options)
            logger.info(f"{protocol.upper()}: Created Zero-Bus stream to {table_name}")

            # Get selected sensors from config (empty list = all sensors)
            selected_sensors = config.get("selected_sensors", [])

            while self.streaming_active.get(protocol, False):
                now_utc = datetime.now(timezone.utc)
                now_us = int(now_utc.timestamp() * 1_000_000)  # Microseconds since epoch as integer

                # Create individual records for each sensor matching table schema
                # Handle different simulator data structures
                if protocol == "modbus":
                    # Modbus: address -> (path, sensor_sim)
                    all_items = list(simulator.simulators.items())
                else:
                    # OPC-UA and MQTT: path -> sensor_sim
                    all_items = list(simulator.simulators.items())

                # Apply sensor filtering if specific sensors were selected
                if selected_sensors and len(selected_sensors) > 0:
                    if protocol == "modbus":
                        # Filter by path (second element of tuple)
                        items = [(addr, data) for addr, data in all_items if data[0] in selected_sensors]
                    else:
                        # Filter by path (key)
                        items = [(path, sim) for path, sim in all_items if path in selected_sensors]
                else:
                    # No filter: use all sensors
                    items = all_items

                for key, data in items:
                    # For Modbus, data is (path, sensor_sim); for others, data is sensor_sim
                    if protocol == "modbus":
                        register_address = key  # Modbus uses address as key
                        path = data[0]
                        sensor_sim = data[1]
                    else:
                        register_address = None
                        path = key
                        sensor_sim = data

                    value = sensor_sim.current_value if hasattr(sensor_sim, 'current_value') else sensor_sim.update()

                    # Parse industry/sensor_name from path
                    parts = path.split("/", 1)
                    industry = parts[0] if len(parts) > 0 else "unknown"
                    sensor_name = parts[1] if len(parts) > 1 else path

                    # Get PLC information if available
                    plc_name = ""
                    plc_vendor = ""
                    plc_model = ""
                    if hasattr(self.manager, 'plc_manager') and self.manager.plc_manager:
                        sensor_data = self.manager.get_sensor_value_with_plc(path)
                        if sensor_data:
                            # plc_model contains the full model string (e.g., "ControlLogix 5580")
                            plc_model = sensor_data.get("plc_model", "") or ""
                            plc_name_id = sensor_data.get("plc_name", "") or ""

                            # Get the PLC object to extract vendor information
                            if plc_name_id and self.manager.plc_manager:
                                plc_obj = self.manager.plc_manager.plcs.get(plc_name_id)
                                if plc_obj and hasattr(plc_obj, 'config'):
                                    plc_vendor = plc_obj.config.vendor if hasattr(plc_obj.config, 'vendor') else ""
                                    # Use the full name as plc_name: "{vendor} {model}"
                                    if plc_vendor and plc_model:
                                        plc_name = f"{plc_vendor} {plc_model}"
                                    elif plc_model:
                                        plc_name = plc_model
                                    else:
                                        plc_name = plc_name_id

                    # Create protocol-specific record matching table schema
                    if protocol == "opcua":
                        # OPC-UA schema: event_time, ingest_time, source_name, endpoint, namespace, node_id,
                        #                browse_path, status_code, status, value_type, value, value_num, raw
                        # Use microsecond timestamps for protobuf
                        record = {
                            "event_time": now_us,
                            "ingest_time": now_us,
                            "source_name": source_name,
                            "endpoint": opcua_endpoint,
                            "namespace": 2,
                            "node_id": f"ns=2;s={path}",
                            "browse_path": f"0:Root/0:Objects/2:{industry}/2:{sensor_name}",
                            "status_code": 0,  # 0 = Good status
                            "status": "Good",
                            "value_type": sensor_sim.config.sensor_type.value if hasattr(sensor_sim.config, 'sensor_type') else "float",
                            "value": str(value),
                            "value_num": float(value) if isinstance(value, (int, float)) else 0.0,
                            "raw": b"",  # Empty bytes for protobuf
                            "plc_name": plc_name,
                            "plc_vendor": plc_vendor,
                            "plc_model": plc_model
                        }
                    elif protocol == "mqtt":
                        # MQTT schema: event_time, ingest_time, source_name, topic, industry, sensor_name,
                        #              value, value_string, unit, sensor_type, timestamp_ms, qos, retain, plc_name, plc_vendor, plc_model
                        record = {
                            "event_time": now_us,
                            "ingest_time": now_us,
                            "source_name": source_name,
                            "topic": f"sensors/{path}/value",
                            "industry": industry,
                            "sensor_name": sensor_name,
                            "value": float(value) if isinstance(value, (int, float)) else None,
                            "value_string": str(value),
                            "unit": sensor_sim.config.unit if hasattr(sensor_sim.config, 'unit') else "",
                            "sensor_type": sensor_sim.config.sensor_type.value if hasattr(sensor_sim.config, 'sensor_type') else "float",
                            "timestamp_ms": int(now_utc.timestamp() * 1000),
                            "qos": 1,
                            "retain": False,
                            "plc_name": plc_name,
                            "plc_vendor": plc_vendor,
                            "plc_model": plc_model
                        }
                    elif protocol == "modbus":
                        # Modbus Bronze Record Schema (matches modbus_bronze.proto)
                        # Fields: event_time, ingest_time, source_name, slave_id, register_address,
                        # register_type, industry, sensor_name, sensor_path, sensor_type, unit,
                        # raw_value (double), scaled_value (int32), scale_factor (int32)

                        # Get scale factor from Modbus config (must be int32 for proto)
                        scale_factor = 10  # Default from config
                        if hasattr(self.config, 'modbus') and hasattr(self.config.modbus, 'scale_factor'):
                            scale_factor = int(self.config.modbus.scale_factor)

                        # raw_value is the original sensor reading (double)
                        raw_value = float(value) if isinstance(value, (int, float)) else 0.0

                        # scaled_value is the 16-bit integer for Modbus register (raw_value * scale_factor)
                        scaled_value = int(raw_value * scale_factor)
                        # Clamp to 16-bit signed integer range
                        scaled_value = max(-32768, min(32767, scaled_value))

                        # Timestamps in microseconds (int64 as per protobuf)
                        record = {
                            "event_time": now_us,
                            "ingest_time": now_us,
                            "source_name": source_name,
                            "slave_id": int(self.config.modbus.slave_id if hasattr(self.config, 'modbus') else 1),
                            "register_address": int(register_address if register_address is not None else 0),
                            "register_type": "holding",
                            "industry": industry,
                            "sensor_name": sensor_name,
                            "sensor_path": path if isinstance(path, str) else f"{industry}/{sensor_name}",
                            "sensor_type": sensor_sim.config.sensor_type.value if hasattr(sensor_sim.config, 'sensor_type') else "float",
                            "unit": sensor_sim.config.unit if hasattr(sensor_sim.config, 'unit') else "",
                            "raw_value": raw_value,
                            "scaled_value": scaled_value,
                            "scale_factor": scale_factor,
                            "plc_name": plc_name,
                            "plc_vendor": plc_vendor,
                            "plc_model": plc_model
                        }
                    else:
                        logger.error(f"Unknown protocol: {protocol}")
                        continue

                    try:
                        # Convert dict to protobuf message before ingesting
                        proto_record = dict_to_protobuf(protocol, record)
                        ack = await stream.ingest_record(proto_record)
                        await ack
                        record_count += 1
                    except Exception as e:
                        logger.error(f"{protocol.upper()} record ingest error for {path}: {e}")
                        # Continue with next sensor instead of stopping
                        continue

                # Flush after batch
                try:
                    await stream.flush()
                    if record_count % 100 == 0:
                        logger.info(f"{protocol.upper()}: Streamed {record_count} records to {table_name}")
                except Exception as e:
                    logger.error(f"{protocol.upper()} flush error: {e}")

                # Wait for next interval
                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            logger.info(f"{protocol.upper()} streaming cancelled")
        except Exception as e:
            logger.exception(f"{protocol.upper()} streaming failed: {e}")
        finally:
            if stream:
                try:
                    await stream.close()
                    logger.info(f"{protocol.upper()} stream closed")
                except Exception as e:
                    logger.error(f"Error closing stream: {e}")
            self.streaming_active[protocol] = False
            logger.info(f"{protocol.upper()} streaming stopped. Total records: {record_count}")

    async def handle_zerobus_config_save(self, request: web.Request) -> web.Response:
        """Save Zero-Bus configuration for a protocol with encrypted credentials."""
        try:
            data = await request.json()
            protocol = data.get("protocol")
            config = data.get("config")

            if not protocol or not config:
                return web.json_response({"success": False, "message": "Missing protocol or config"})

            # Validate required fields
            required_fields = ["workspace_host", "zerobus_endpoint"]
            for field in required_fields:
                if not config.get(field):
                    return web.json_response({
                        "success": False,
                        "message": f"Missing required field: {field}"
                    })

            # Save configuration with encrypted credentials
            config_file = self.credential_manager.save_config(protocol, config)

            return web.json_response({
                "success": True,
                "message": f"Configuration saved securely (credentials encrypted)",
                "config_file": str(config_file)
            })

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            return web.json_response({
                "success": False,
                "message": str(e),
                "detail": error_detail
            })

    async def handle_zerobus_start(self, request: web.Request) -> web.Response:
        """Start Zero-Bus streaming for a protocol."""
        try:
            data = await request.json()
            protocol = data.get("protocol")

            if not protocol:
                return web.json_response({"success": False, "message": "Missing protocol"})

            # Check if already streaming
            if self.streaming_active.get(protocol, False):
                return web.json_response({
                    "success": False,
                    "message": f"{protocol.upper()} streaming is already active"
                })

            # Load saved configuration
            config = self.credential_manager.load_config(protocol)
            if not config:
                return web.json_response({
                    "success": False,
                    "message": f"No saved configuration found for {protocol}. Please save configuration first."
                })

            # Validate required fields
            if not config.get("workspace_host") or not config.get("zerobus_endpoint"):
                return web.json_response({
                    "success": False,
                    "message": "Invalid configuration: missing workspace_host or zerobus_endpoint"
                })

            # Start streaming task
            task = asyncio.create_task(self._stream_to_zerobus(protocol, config))
            self.streaming_tasks[protocol] = task
            self.streaming_active[protocol] = True

            return web.json_response({
                "success": True,
                "message": f"{protocol.upper()} streaming started successfully"
            })

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"Error starting Zero-Bus stream: {error_detail}")
            return web.json_response({
                "success": False,
                "message": str(e),
                "detail": error_detail
            })

    async def handle_zerobus_stop(self, request: web.Request) -> web.Response:
        """Stop Zero-Bus streaming for a protocol."""
        try:
            data = await request.json()
            protocol = data.get("protocol")

            if not protocol:
                return web.json_response({"success": False, "message": "Missing protocol"})

            # Check if streaming is active
            if not self.streaming_active.get(protocol, False):
                return web.json_response({
                    "success": False,
                    "message": f"{protocol.upper()} streaming is not active"
                })

            # Cancel the task
            task = self.streaming_tasks.get(protocol)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            self.streaming_active[protocol] = False
            self.streaming_tasks.pop(protocol, None)

            return web.json_response({
                "success": True,
                "message": f"{protocol.upper()} streaming stopped successfully"
            })

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"Error stopping Zero-Bus stream: {error_detail}")
            return web.json_response({
                "success": False,
                "message": str(e),
                "detail": error_detail
            })

    async def handle_zerobus_status(self, request: web.Request) -> web.Response:
        """Get Zero-Bus streaming status for all protocols."""
        try:
            status = {}
            for protocol in ["opcua", "mqtt", "modbus"]:
                active = self.streaming_active.get(protocol, False)
                status[protocol] = {
                    "active": active,
                    "has_config": self.credential_manager.load_config(protocol) is not None
                }

            return web.json_response({
                "success": True,
                "status": status
            })

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"Error getting Zero-Bus status: {error_detail}")
            return web.json_response({
                "success": False,
                "message": str(e),
                "detail": error_detail
            })

    async def _stream_to_zerobus(self, protocol: str, config: dict[str, Any]):
        """Background task that streams sensor data to Zero-Bus."""
        from zerobus.sdk.aio import ZerobusSdk
        from zerobus.sdk.shared import TableProperties

        logger.info(f"Starting {protocol.upper()} to Zero-Bus streaming")

        # Get direct credentials from config
        auth = config.get("auth", {})
        client_id = auth.get("client_id", "").strip()
        client_secret = auth.get("client_secret", "").strip()

        if not client_id or not client_secret:
            logger.error(f"{protocol.upper()}: Missing OAuth credentials")
            self.streaming_active[protocol] = False
            return

        # Get connection details
        workspace_host = config.get("workspace_host", "").strip().rstrip("/")
        zerobus_endpoint = config.get("zerobus_endpoint", "").strip()
        target = config.get("target", {})

        catalog = target.get("catalog", "").strip()
        schema = target.get("schema", "").strip()
        table = target.get("table", "").strip()

        if not workspace_host or not zerobus_endpoint or not catalog or not schema or not table:
            logger.error(f"{protocol.upper()}: Invalid configuration")
            self.streaming_active[protocol] = False
            return

        table_name = f"{catalog}.{schema}.{table}"

        # Initialize SDK
        sdk = ZerobusSdk(zerobus_endpoint, workspace_host)

        # Get protobuf descriptor for this protocol
        descriptor = get_protobuf_descriptor(protocol)
        table_properties = TableProperties(table_name, descriptor_proto=descriptor)

        # Configure stream for protobuf record type
        from zerobus.sdk.shared import RecordType, StreamConfigurationOptions
        stream_options = StreamConfigurationOptions(
            record_type=RecordType.PROTO,
            max_inflight_records=1000,
            recovery=True,
            flush_timeout_ms=60000,
            server_lack_of_ack_timeout_ms=60000,
        )

        # Get protocol-specific data source from manager's simulators dict
        simulator = self.manager.simulators.get(protocol)
        if not simulator:
            logger.error(f"{protocol.upper()} simulator not available in manager")
            self.streaming_active[protocol] = False
            return

        # Stream data at configured interval (default 5 seconds)
        interval = config.get("streaming_interval_seconds", 5)
        record_count = 0

        # Get endpoint for OPC-UA
        opcua_endpoint = getattr(self.config, 'opcua', None)
        if opcua_endpoint and hasattr(opcua_endpoint, 'endpoint'):
            opcua_endpoint = opcua_endpoint.endpoint
        else:
            opcua_endpoint = "opc.tcp://0.0.0.0:4840/ot-simulator/server/"
        source_name = f"{protocol}_simulator"

        # Create stream once outside the loop
        stream = None
        try:
            stream = await sdk.create_stream(client_id, client_secret, table_properties, stream_options)
            logger.info(f"{protocol.upper()}: Created Zero-Bus stream to {table_name}")

            # Get selected sensors from config (empty list = all sensors)
            selected_sensors = config.get("selected_sensors", [])

            while self.streaming_active.get(protocol, False):
                now_utc = datetime.now(timezone.utc)
                now_us = int(now_utc.timestamp() * 1_000_000)  # Microseconds since epoch as integer

                # Create individual records for each sensor matching table schema
                # Handle different simulator data structures
                if protocol == "modbus":
                    # Modbus: address -> (path, sensor_sim)
                    all_items = list(simulator.simulators.items())
                else:
                    # OPC-UA and MQTT: path -> sensor_sim
                    all_items = list(simulator.simulators.items())

                # Apply sensor filtering if specific sensors were selected
                if selected_sensors and len(selected_sensors) > 0:
                    if protocol == "modbus":
                        # Filter by path (second element of tuple)
                        items = [(addr, data) for addr, data in all_items if data[0] in selected_sensors]
                    else:
                        # Filter by path (key)
                        items = [(path, sim) for path, sim in all_items if path in selected_sensors]
                else:
                    # No filter: use all sensors
                    items = all_items

                for key, data in items:
                    # For Modbus, data is (path, sensor_sim); for others, data is sensor_sim
                    if protocol == "modbus":
                        register_address = key  # Modbus uses address as key
                        path = data[0]
                        sensor_sim = data[1]
                    else:
                        register_address = None
                        path = key
                        sensor_sim = data

                    value = sensor_sim.current_value if hasattr(sensor_sim, 'current_value') else sensor_sim.update()

                    # Parse industry/sensor_name from path
                    parts = path.split("/", 1)
                    industry = parts[0] if len(parts) > 0 else "unknown"
                    sensor_name = parts[1] if len(parts) > 1 else path

                    # Get PLC information if available
                    plc_name = ""
                    plc_vendor = ""
                    plc_model = ""
                    if hasattr(self.manager, 'plc_manager') and self.manager.plc_manager:
                        sensor_data = self.manager.get_sensor_value_with_plc(path)
                        if sensor_data:
                            # plc_model contains the full model string (e.g., "ControlLogix 5580")
                            plc_model = sensor_data.get("plc_model", "") or ""
                            plc_name_id = sensor_data.get("plc_name", "") or ""

                            # Get the PLC object to extract vendor information
                            if plc_name_id and self.manager.plc_manager:
                                plc_obj = self.manager.plc_manager.plcs.get(plc_name_id)
                                if plc_obj and hasattr(plc_obj, 'config'):
                                    plc_vendor = plc_obj.config.vendor if hasattr(plc_obj.config, 'vendor') else ""
                                    # Use the full name as plc_name: "{vendor} {model}"
                                    if plc_vendor and plc_model:
                                        plc_name = f"{plc_vendor} {plc_model}"
                                    elif plc_model:
                                        plc_name = plc_model
                                    else:
                                        plc_name = plc_name_id

                    # Create protocol-specific record matching table schema
                    if protocol == "opcua":
                        # OPC-UA schema: event_time, ingest_time, source_name, endpoint, namespace, node_id,
                        #                browse_path, status_code, status, value_type, value, value_num, raw
                        # Use microsecond timestamps for protobuf
                        record = {
                            "event_time": now_us,
                            "ingest_time": now_us,
                            "source_name": source_name,
                            "endpoint": opcua_endpoint,
                            "namespace": 2,
                            "node_id": f"ns=2;s={path}",
                            "browse_path": f"0:Root/0:Objects/2:{industry}/2:{sensor_name}",
                            "status_code": 0,  # 0 = Good status
                            "status": "Good",
                            "value_type": sensor_sim.config.sensor_type.value if hasattr(sensor_sim.config, 'sensor_type') else "float",
                            "value": str(value),
                            "value_num": float(value) if isinstance(value, (int, float)) else 0.0,
                            "raw": b"",  # Empty bytes for protobuf
                            "plc_name": plc_name,
                            "plc_vendor": plc_vendor,
                            "plc_model": plc_model
                        }
                    elif protocol == "mqtt":
                        # MQTT schema: event_time, ingest_time, source_name, topic, industry, sensor_name,
                        #              value, value_string, unit, sensor_type, timestamp_ms, qos, retain, plc_name, plc_vendor, plc_model
                        record = {
                            "event_time": now_us,
                            "ingest_time": now_us,
                            "source_name": source_name,
                            "topic": f"sensors/{path}/value",
                            "industry": industry,
                            "sensor_name": sensor_name,
                            "value": float(value) if isinstance(value, (int, float)) else None,
                            "value_string": str(value),
                            "unit": sensor_sim.config.unit if hasattr(sensor_sim.config, 'unit') else "",
                            "sensor_type": sensor_sim.config.sensor_type.value if hasattr(sensor_sim.config, 'sensor_type') else "float",
                            "timestamp_ms": int(now_utc.timestamp() * 1000),
                            "qos": 1,
                            "retain": False,
                            "plc_name": plc_name,
                            "plc_vendor": plc_vendor,
                            "plc_model": plc_model
                        }
                    elif protocol == "modbus":
                        # Modbus Bronze Record Schema (matches modbus_bronze.proto)
                        # Fields: event_time, ingest_time, source_name, slave_id, register_address,
                        # register_type, industry, sensor_name, sensor_path, sensor_type, unit,
                        # raw_value (double), scaled_value (int32), scale_factor (int32)

                        # Get scale factor from Modbus config (must be int32 for proto)
                        scale_factor = 10  # Default from config
                        if hasattr(self.config, 'modbus') and hasattr(self.config.modbus, 'scale_factor'):
                            scale_factor = int(self.config.modbus.scale_factor)

                        # raw_value is the original sensor reading (double)
                        raw_value = float(value) if isinstance(value, (int, float)) else 0.0

                        # scaled_value is the 16-bit integer for Modbus register (raw_value * scale_factor)
                        scaled_value = int(raw_value * scale_factor)
                        # Clamp to 16-bit signed integer range
                        scaled_value = max(-32768, min(32767, scaled_value))

                        # Timestamps in microseconds (int64 as per protobuf)
                        record = {
                            "event_time": now_us,
                            "ingest_time": now_us,
                            "source_name": source_name,
                            "slave_id": int(self.config.modbus.slave_id if hasattr(self.config, 'modbus') else 1),
                            "register_address": int(register_address if register_address is not None else 0),
                            "register_type": "holding",
                            "industry": industry,
                            "sensor_name": sensor_name,
                            "sensor_path": path if isinstance(path, str) else f"{industry}/{sensor_name}",
                            "sensor_type": sensor_sim.config.sensor_type.value if hasattr(sensor_sim.config, 'sensor_type') else "float",
                            "unit": sensor_sim.config.unit if hasattr(sensor_sim.config, 'unit') else "",
                            "raw_value": raw_value,
                            "scaled_value": scaled_value,
                            "scale_factor": scale_factor,
                            "plc_name": plc_name,
                            "plc_vendor": plc_vendor,
                            "plc_model": plc_model
                        }
                    else:
                        logger.error(f"Unknown protocol: {protocol}")
                        continue

                    try:
                        # Convert dict to protobuf message before ingesting
                        proto_record = dict_to_protobuf(protocol, record)
                        ack = await stream.ingest_record(proto_record)
                        await ack
                        record_count += 1
                    except Exception as e:
                        logger.error(f"{protocol.upper()} record ingest error for {path}: {e}")
                        # Continue with next sensor instead of stopping
                        continue

                # Flush after batch
                try:
                    await stream.flush()
                    if record_count % 100 == 0:
                        logger.info(f"{protocol.upper()}: Streamed {record_count} records to {table_name}")
                except Exception as e:
                    logger.error(f"{protocol.upper()} flush error: {e}")

                # Wait for next interval
                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            logger.info(f"{protocol.upper()} streaming cancelled")
        except Exception as e:
            logger.exception(f"{protocol.upper()} streaming failed: {e}")
        finally:
            if stream:
                try:
                    await stream.close()
                    logger.info(f"{protocol.upper()} stream closed")
                except Exception as e:
                    logger.error(f"Error closing stream: {e}")
            self.streaming_active[protocol] = False
            logger.info(f"{protocol.upper()} streaming stopped. Total records: {record_count}")

    async def handle_zerobus_test(self, request: web.Request) -> web.Response:
        """Test Zero-Bus connection for a protocol."""
        try:
            import os

            data = await request.json()
            protocol = data.get("protocol")
            config = data.get("config")

            if not protocol or not config:
                return web.json_response({"success": False, "message": "Missing protocol or config"})

            # Import the Zero-Bus SDK directly
            from zerobus.sdk.aio import ZerobusSdk
            from zerobus.sdk.shared import RecordType, StreamConfigurationOptions, TableProperties

            # Get direct credentials from config
            auth_config = config.get("auth", {})
            client_id = auth_config.get("client_id", "").strip()
            client_secret = auth_config.get("client_secret", "").strip()

            if not client_id or not client_secret:
                return web.json_response({
                    "success": False,
                    "message": "OAuth Client ID and Client Secret are required"
                })

            # Get connection details
            workspace_host = config.get("workspace_host", "").strip().rstrip("/")
            zerobus_endpoint = config.get("zerobus_endpoint", "").strip()
            target = config.get("target", {})

            catalog = target.get("catalog", "").strip()
            schema = target.get("schema", "").strip()
            table = target.get("table", "").strip()

            if not workspace_host or not zerobus_endpoint or not catalog or not schema or not table:
                return web.json_response({
                    "success": False,
                    "message": "Missing required fields"
                })

            table_name = f"{catalog}.{schema}.{table}"

            # Create test record as a dict
            from datetime import datetime, timezone
            now_utc = datetime.now(timezone.utc)
            now_us = int(now_utc.timestamp() * 1_000_000)
            source_name = f"{protocol}_simulator_test"
            endpoint = f"test://{protocol}"

            # Create protocol-specific test dict
            if protocol.lower() == "opcua":
                test_dict = {
                    "event_time": now_us,
                    "ingest_time": now_us,
                    "source_name": source_name,
                    "endpoint": endpoint,
                    "namespace": 2,
                    "node_id": "ns=2;s=test_node",
                    "browse_path": "0:Root/0:Objects/2:Test",
                    "status_code": 0,
                    "status": "Good",
                    "value_type": "Double",
                    "value": "42.0",
                    "value_num": 42.0,
                    "raw": b""
                }
            elif protocol.lower() == "mqtt":
                test_dict = {
                    "event_time": now_us,
                    "ingest_time": now_us,
                    "source_name": source_name,
                    "topic": "test/topic",
                    "industry": "test",
                    "sensor_name": "test_sensor",
                    "value": 42.0,
                    "value_string": "42.0",
                    "unit": "units",
                    "sensor_type": "temperature",
                    "timestamp_ms": int(now_utc.timestamp() * 1000),
                    "qos": 1,
                    "retain": False
                }
            elif protocol.lower() == "modbus":
                test_dict = {
                    "event_time": now_us,
                    "ingest_time": now_us,
                    "source_name": source_name,
                    "slave_id": 1,
                    "register_address": 0,
                    "register_type": "holding",
                    "industry": "test",
                    "sensor_name": "test_sensor",
                    "sensor_path": "test/sensor",
                    "sensor_type": "temperature",
                    "unit": "°C",
                    "raw_value": 42.0,
                    "scaled_value": 420,
                    "scale_factor": 10
                }
            else:
                return web.json_response({"success": False, "message": f"Unknown protocol: {protocol}"})

            # Convert dict to protobuf
            test_record = dict_to_protobuf(protocol, test_dict)

            # Test the connection using ZerobusSdk directly
            from zerobus.sdk.shared import RecordType, StreamConfigurationOptions

            sdk = ZerobusSdk(zerobus_endpoint, workspace_host)

            # Get protobuf descriptor for this protocol
            descriptor = get_protobuf_descriptor(protocol)
            table_properties = TableProperties(table_name, descriptor_proto=descriptor)

            # Configure stream for protobuf record type
            stream_options = StreamConfigurationOptions(
                record_type=RecordType.PROTO,
                max_inflight_records=1000,
                recovery=True,
                flush_timeout_ms=60000,
                server_lack_of_ack_timeout_ms=60000,
            )

            # Create stream
            stream = await sdk.create_stream(client_id, client_secret, table_properties, stream_options)

            err: Exception | None = None
            try:
                # Ingest test record (already a protobuf message)
                ack = await stream.ingest_record(test_record)
                await ack
                await stream.flush()

                return web.json_response({
                    "success": True,
                    "table_name": table_name,
                    "stream_id": stream.stream_id,
                    "message": f"Successfully sent test record to {table_name}"
                })
            except Exception as e:
                err = e
                raise
            finally:
                try:
                    await stream.close()
                except Exception:
                    # Don't mask the real ingest/create error with a close() error
                    if err is None:
                        raise

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            return web.json_response({
                "success": False,
                "message": str(e),
                "detail": error_detail
            })

    async def handle_zerobus_start(self, request: web.Request) -> web.Response:
        """Start Zero-Bus streaming for a protocol."""
        try:
            data = await request.json()
            protocol = data.get("protocol")

            if not protocol:
                return web.json_response({"success": False, "message": "Missing protocol"})

            # Check if already streaming
            if self.streaming_active.get(protocol, False):
                return web.json_response({
                    "success": False,
                    "message": f"{protocol.upper()} streaming is already active"
                })

            # Load saved configuration
            config = self.credential_manager.load_config(protocol)
            if not config:
                return web.json_response({
                    "success": False,
                    "message": f"No saved configuration found for {protocol}. Please save configuration first."
                })

            # Validate required fields
            if not config.get("workspace_host") or not config.get("zerobus_endpoint"):
                return web.json_response({
                    "success": False,
                    "message": "Invalid configuration: missing workspace_host or zerobus_endpoint"
                })

            # Start streaming task
            task = asyncio.create_task(self._stream_to_zerobus(protocol, config))
            self.streaming_tasks[protocol] = task
            self.streaming_active[protocol] = True

            return web.json_response({
                "success": True,
                "message": f"{protocol.upper()} streaming started successfully"
            })

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"Error starting Zero-Bus stream: {error_detail}")
            return web.json_response({
                "success": False,
                "message": str(e),
                "detail": error_detail
            })

    async def handle_zerobus_stop(self, request: web.Request) -> web.Response:
        """Stop Zero-Bus streaming for a protocol."""
        try:
            data = await request.json()
            protocol = data.get("protocol")

            if not protocol:
                return web.json_response({"success": False, "message": "Missing protocol"})

            # Check if streaming is active
            if not self.streaming_active.get(protocol, False):
                return web.json_response({
                    "success": False,
                    "message": f"{protocol.upper()} streaming is not active"
                })

            # Cancel the task
            task = self.streaming_tasks.get(protocol)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            self.streaming_active[protocol] = False
            self.streaming_tasks.pop(protocol, None)

            return web.json_response({
                "success": True,
                "message": f"{protocol.upper()} streaming stopped successfully"
            })

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"Error stopping Zero-Bus stream: {error_detail}")
            return web.json_response({
                "success": False,
                "message": str(e),
                "detail": error_detail
            })

    async def handle_zerobus_status(self, request: web.Request) -> web.Response:
        """Get Zero-Bus streaming status for all protocols."""
        try:
            status = {}
            for protocol in ["opcua", "mqtt", "modbus"]:
                active = self.streaming_active.get(protocol, False)
                status[protocol] = {
                    "active": active,
                    "has_config": self.credential_manager.load_config(protocol) is not None
                }

            return web.json_response({
                "success": True,
                "status": status
            })

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"Error getting Zero-Bus status: {error_detail}")
            return web.json_response({
                "success": False,
                "message": str(e),
                "detail": error_detail
            })

    async def _stream_to_zerobus(self, protocol: str, config: dict[str, Any]):
        """Background task that streams sensor data to Zero-Bus."""
        from zerobus.sdk.aio import ZerobusSdk
        from zerobus.sdk.shared import TableProperties

        logger.info(f"Starting {protocol.upper()} to Zero-Bus streaming")

        # Get direct credentials from config
        auth = config.get("auth", {})
        client_id = auth.get("client_id", "").strip()
        client_secret = auth.get("client_secret", "").strip()

        if not client_id or not client_secret:
            logger.error(f"{protocol.upper()}: Missing OAuth credentials")
            self.streaming_active[protocol] = False
            return

        # Get connection details
        workspace_host = config.get("workspace_host", "").strip().rstrip("/")
        zerobus_endpoint = config.get("zerobus_endpoint", "").strip()
        target = config.get("target", {})

        catalog = target.get("catalog", "").strip()
        schema = target.get("schema", "").strip()
        table = target.get("table", "").strip()

        if not workspace_host or not zerobus_endpoint or not catalog or not schema or not table:
            logger.error(f"{protocol.upper()}: Invalid configuration")
            self.streaming_active[protocol] = False
            return

        table_name = f"{catalog}.{schema}.{table}"

        # Initialize SDK
        sdk = ZerobusSdk(zerobus_endpoint, workspace_host)

        # Get protobuf descriptor for this protocol
        descriptor = get_protobuf_descriptor(protocol)
        table_properties = TableProperties(table_name, descriptor_proto=descriptor)

        # Configure stream for protobuf record type
        from zerobus.sdk.shared import RecordType, StreamConfigurationOptions
        stream_options = StreamConfigurationOptions(
            record_type=RecordType.PROTO,
            max_inflight_records=1000,
            recovery=True,
            flush_timeout_ms=60000,
            server_lack_of_ack_timeout_ms=60000,
        )

        # Get protocol-specific data source from manager's simulators dict
        simulator = self.manager.simulators.get(protocol)
        if not simulator:
            logger.error(f"{protocol.upper()} simulator not available in manager")
            self.streaming_active[protocol] = False
            return

        # Stream data at configured interval (default 5 seconds)
        interval = config.get("streaming_interval_seconds", 5)
        record_count = 0

        # Get endpoint for OPC-UA
        opcua_endpoint = getattr(self.config, 'opcua', None)
        if opcua_endpoint and hasattr(opcua_endpoint, 'endpoint'):
            opcua_endpoint = opcua_endpoint.endpoint
        else:
            opcua_endpoint = "opc.tcp://0.0.0.0:4840/ot-simulator/server/"
        source_name = f"{protocol}_simulator"

        # Create stream once outside the loop
        stream = None
        try:
            stream = await sdk.create_stream(client_id, client_secret, table_properties, stream_options)
            logger.info(f"{protocol.upper()}: Created Zero-Bus stream to {table_name}")

            # Get selected sensors from config (empty list = all sensors)
            selected_sensors = config.get("selected_sensors", [])

            while self.streaming_active.get(protocol, False):
                now_utc = datetime.now(timezone.utc)
                now_us = int(now_utc.timestamp() * 1_000_000)  # Microseconds since epoch as integer

                # Create individual records for each sensor matching table schema
                # Handle different simulator data structures
                if protocol == "modbus":
                    # Modbus: address -> (path, sensor_sim)
                    all_items = list(simulator.simulators.items())
                else:
                    # OPC-UA and MQTT: path -> sensor_sim
                    all_items = list(simulator.simulators.items())

                # Apply sensor filtering if specific sensors were selected
                if selected_sensors and len(selected_sensors) > 0:
                    if protocol == "modbus":
                        # Filter by path (second element of tuple)
                        items = [(addr, data) for addr, data in all_items if data[0] in selected_sensors]
                    else:
                        # Filter by path (key)
                        items = [(path, sim) for path, sim in all_items if path in selected_sensors]
                else:
                    # No filter: use all sensors
                    items = all_items

                for key, data in items:
                    # For Modbus, data is (path, sensor_sim); for others, data is sensor_sim
                    if protocol == "modbus":
                        register_address = key  # Modbus uses address as key
                        path = data[0]
                        sensor_sim = data[1]
                    else:
                        register_address = None
                        path = key
                        sensor_sim = data

                    value = sensor_sim.current_value if hasattr(sensor_sim, 'current_value') else sensor_sim.update()

                    # Parse industry/sensor_name from path
                    parts = path.split("/", 1)
                    industry = parts[0] if len(parts) > 0 else "unknown"
                    sensor_name = parts[1] if len(parts) > 1 else path

                    # Get PLC information if available
                    plc_name = ""
                    plc_vendor = ""
                    plc_model = ""
                    if hasattr(self.manager, 'plc_manager') and self.manager.plc_manager:
                        sensor_data = self.manager.get_sensor_value_with_plc(path)
                        if sensor_data:
                            # plc_model contains the full model string (e.g., "ControlLogix 5580")
                            plc_model = sensor_data.get("plc_model", "") or ""
                            plc_name_id = sensor_data.get("plc_name", "") or ""

                            # Get the PLC object to extract vendor information
                            if plc_name_id and self.manager.plc_manager:
                                plc_obj = self.manager.plc_manager.plcs.get(plc_name_id)
                                if plc_obj and hasattr(plc_obj, 'config'):
                                    plc_vendor = plc_obj.config.vendor if hasattr(plc_obj.config, 'vendor') else ""
                                    # Use the full name as plc_name: "{vendor} {model}"
                                    if plc_vendor and plc_model:
                                        plc_name = f"{plc_vendor} {plc_model}"
                                    elif plc_model:
                                        plc_name = plc_model
                                    else:
                                        plc_name = plc_name_id

                    # Create protocol-specific record matching table schema
                    if protocol == "opcua":
                        # OPC-UA schema: event_time, ingest_time, source_name, endpoint, namespace, node_id,
                        #                browse_path, status_code, status, value_type, value, value_num, raw
                        # Use microsecond timestamps for protobuf
                        record = {
                            "event_time": now_us,
                            "ingest_time": now_us,
                            "source_name": source_name,
                            "endpoint": opcua_endpoint,
                            "namespace": 2,
                            "node_id": f"ns=2;s={path}",
                            "browse_path": f"0:Root/0:Objects/2:{industry}/2:{sensor_name}",
                            "status_code": 0,  # 0 = Good status
                            "status": "Good",
                            "value_type": sensor_sim.config.sensor_type.value if hasattr(sensor_sim.config, 'sensor_type') else "float",
                            "value": str(value),
                            "value_num": float(value) if isinstance(value, (int, float)) else 0.0,
                            "raw": b"",  # Empty bytes for protobuf
                            "plc_name": plc_name,
                            "plc_vendor": plc_vendor,
                            "plc_model": plc_model
                        }
                    elif protocol == "mqtt":
                        # MQTT schema: event_time, ingest_time, source_name, topic, industry, sensor_name,
                        #              value, value_string, unit, sensor_type, timestamp_ms, qos, retain, plc_name, plc_vendor, plc_model
                        record = {
                            "event_time": now_us,
                            "ingest_time": now_us,
                            "source_name": source_name,
                            "topic": f"sensors/{path}/value",
                            "industry": industry,
                            "sensor_name": sensor_name,
                            "value": float(value) if isinstance(value, (int, float)) else None,
                            "value_string": str(value),
                            "unit": sensor_sim.config.unit if hasattr(sensor_sim.config, 'unit') else "",
                            "sensor_type": sensor_sim.config.sensor_type.value if hasattr(sensor_sim.config, 'sensor_type') else "float",
                            "timestamp_ms": int(now_utc.timestamp() * 1000),
                            "qos": 1,
                            "retain": False,
                            "plc_name": plc_name,
                            "plc_vendor": plc_vendor,
                            "plc_model": plc_model
                        }
                    elif protocol == "modbus":
                        # Modbus Bronze Record Schema (matches modbus_bronze.proto)
                        # Fields: event_time, ingest_time, source_name, slave_id, register_address,
                        # register_type, industry, sensor_name, sensor_path, sensor_type, unit,
                        # raw_value (double), scaled_value (int32), scale_factor (int32)

                        # Get scale factor from Modbus config (must be int32 for proto)
                        scale_factor = 10  # Default from config
                        if hasattr(self.config, 'modbus') and hasattr(self.config.modbus, 'scale_factor'):
                            scale_factor = int(self.config.modbus.scale_factor)

                        # raw_value is the original sensor reading (double)
                        raw_value = float(value) if isinstance(value, (int, float)) else 0.0

                        # scaled_value is the 16-bit integer for Modbus register (raw_value * scale_factor)
                        scaled_value = int(raw_value * scale_factor)
                        # Clamp to 16-bit signed integer range
                        scaled_value = max(-32768, min(32767, scaled_value))

                        # Timestamps in microseconds (int64 as per protobuf)
                        record = {
                            "event_time": now_us,
                            "ingest_time": now_us,
                            "source_name": source_name,
                            "slave_id": int(self.config.modbus.slave_id if hasattr(self.config, 'modbus') else 1),
                            "register_address": int(register_address if register_address is not None else 0),
                            "register_type": "holding",
                            "industry": industry,
                            "sensor_name": sensor_name,
                            "sensor_path": path if isinstance(path, str) else f"{industry}/{sensor_name}",
                            "sensor_type": sensor_sim.config.sensor_type.value if hasattr(sensor_sim.config, 'sensor_type') else "float",
                            "unit": sensor_sim.config.unit if hasattr(sensor_sim.config, 'unit') else "",
                            "raw_value": raw_value,
                            "scaled_value": scaled_value,
                            "scale_factor": scale_factor,
                            "plc_name": plc_name,
                            "plc_vendor": plc_vendor,
                            "plc_model": plc_model
                        }
                    else:
                        logger.error(f"Unknown protocol: {protocol}")
                        continue

                    try:
                        # Convert dict to protobuf message before ingesting
                        proto_record = dict_to_protobuf(protocol, record)
                        ack = await stream.ingest_record(proto_record)
                        await ack
                        record_count += 1
                    except Exception as e:
                        logger.error(f"{protocol.upper()} record ingest error for {path}: {e}")
                        # Continue with next sensor instead of stopping
                        continue

                # Flush after batch
                try:
                    await stream.flush()
                    if record_count % 100 == 0:
                        logger.info(f"{protocol.upper()}: Streamed {record_count} records to {table_name}")
                except Exception as e:
                    logger.error(f"{protocol.upper()} flush error: {e}")

                # Wait for next interval
                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            logger.info(f"{protocol.upper()} streaming cancelled")
        except Exception as e:
            logger.exception(f"{protocol.upper()} streaming failed: {e}")
        finally:
            if stream:
                try:
                    await stream.close()
                    logger.info(f"{protocol.upper()} stream closed")
                except Exception as e:
                    logger.error(f"Error closing stream: {e}")
            self.streaming_active[protocol] = False
            logger.info(f"{protocol.upper()} streaming stopped. Total records: {record_count}")

    async def handle_opcua_thing_description(self, request: web.Request) -> web.Response:
        """Generate and return W3C WoT Thing Description for OPC-UA server."""
        try:
            from ot_simulator.wot import ThingDescriptionGenerator

            # Get OPC-UA endpoint from config
            opcua_endpoint = getattr(self.config, 'opcua', None)
            if opcua_endpoint and hasattr(opcua_endpoint, 'endpoint'):
                base_url = opcua_endpoint.endpoint
            else:
                base_url = "opc.tcp://0.0.0.0:4840/ot-simulator/server/"

            # Create TD generator
            td_generator = ThingDescriptionGenerator(
                simulator_manager=self.manager,
                base_url=base_url,
                namespace_uri="http://databricks.com/iot-simulator"
            )

            # Generate Thing Description
            td = await td_generator.generate_td()

            return web.json_response(td, content_type="application/td+json")

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"Error generating Thing Description: {error_detail}")
            return web.json_response({
                "error": str(e),
                "detail": error_detail
            }, status=500)
