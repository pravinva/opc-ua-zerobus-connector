"""MQTT Publisher Simulator with realistic industrial data.

Publishes sensor data to an MQTT broker using various payload formats.
Supports JSON, simple string, and Sparkplug B formats.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

try:
    import aiomqtt
except ImportError:
    aiomqtt = None  # type: ignore

try:
    from pysparkplug import Device, EdgeNode, DeviceMetric, DataType
except ImportError:
    Device = None  # type: ignore
    EdgeNode = None  # type: ignore
    DeviceMetric = None  # type: ignore
    DataType = None  # type: ignore

from ot_simulator.config_loader import MQTTConfig
from ot_simulator.sensor_models import IndustryType, SensorSimulator, get_industry_sensors

logger = logging.getLogger("ot_simulator.mqtt")


class MQTTSimulator:
    """MQTT publisher simulator with realistic sensor data."""

    def __init__(self, config: MQTTConfig):
        if aiomqtt is None:
            raise ImportError("aiomqtt package required. Install with: pip install aiomqtt")

        self.config = config
        self.simulators: dict[str, SensorSimulator] = {}
        self.client: aiomqtt.Client | None = None
        self._running = False
        self._message_count = 0

    async def init(self):
        """Initialize MQTT client and sensors."""
        # Create simulators for enabled industries
        industry_types = []
        for industry_name in self.config.industries:
            try:
                industry_types.append(IndustryType(industry_name))
            except ValueError:
                logger.warning(f"Unknown industry type: {industry_name}")

        for industry in industry_types:
            sensors = get_industry_sensors(industry)
            for simulator in sensors:
                path = f"{industry.value}/{simulator.config.name}"
                self.simulators[path] = simulator

        logger.info(
            f"Initialized MQTT publisher with {len(self.simulators)} sensors across {len(industry_types)} industries"
        )

    async def start(self):
        """Start publishing sensor data to MQTT broker.

        If broker connection fails, runs in headless mode where sensors are
        initialized but no publishing occurs. This allows Zero-Bus streaming
        to access sensor data without requiring an MQTT broker.
        """
        if not self.simulators:
            await self.init()

        # Connect to broker
        broker_host = self.config.broker.host
        broker_port = self.config.broker.tls_port if self.config.broker.use_tls else self.config.broker.port

        # Check if broker is running, if not try to start it
        if broker_host in ("localhost", "127.0.0.1"):
            await self._ensure_broker_running(broker_host, broker_port)

        tls_params = None
        if self.config.broker.use_tls:
            import ssl

            tls_params = aiomqtt.TLSParameters(
                ca_certs=None,
                certfile=None,
                keyfile=None,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS,
                ciphers=None,
            )

        self.client = aiomqtt.Client(
            hostname=broker_host,
            port=broker_port,
            username=self.config.auth.username or None,
            password=self.config.auth.password or None,
            identifier=self.config.client_id,
            clean_session=self.config.clean_session,
            keepalive=self.config.keepalive,
            tls_params=tls_params,
        )

        try:
            async with self.client:
                logger.info(f"MQTT client connected to {broker_host}:{broker_port}")
                self._running = True

                try:
                    # Calculate publish interval
                    publish_interval = 1.0 / self.config.publish_rate_hz

                    while self._running:
                        start_time = time.time()

                        if self.config.batch_publish:
                            # Publish all sensors at once
                            await self._publish_batch()
                        else:
                            # Publish sensors individually
                            for path, simulator in self.simulators.items():
                                await self._publish_sensor(path, simulator)

                        self._message_count += len(self.simulators)

                        # Log stats periodically
                        if self._message_count % 1000 == 0:
                            logger.info(f"Published {self._message_count} messages")

                        # Sleep for remaining time to maintain rate
                        elapsed = time.time() - start_time
                        sleep_time = max(0, publish_interval - elapsed)
                        if sleep_time > 0:
                            await asyncio.sleep(sleep_time)

                except asyncio.CancelledError:
                    logger.info("MQTT publisher stopping...")
                    self._running = False
                except Exception as e:
                    logger.exception(f"Error in MQTT publisher: {e}")
                    raise
        except Exception as broker_error:
            # Broker connection failed - run in headless mode
            logger.warning(f"MQTT broker connection failed: {broker_error}")
            logger.info("Running in headless mode - sensors active but not publishing to broker")
            logger.info("Zero-Bus streaming will still work by reading sensor data directly")
            self._running = True

            # Keep simulator running without broker connection
            try:
                while self._running:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                logger.info("MQTT simulator stopping...")
                self._running = False

    async def _ensure_broker_running(self, host: str, port: int):
        """Check if MQTT broker is running and start it if needed."""
        import socket
        import subprocess
        import shutil

        # Check if broker is already running
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                logger.info(f"MQTT broker already running on {host}:{port}")
                return
        except Exception:
            pass

        # Try to start Mosquitto
        mosquitto_path = shutil.which("mosquitto")
        if not mosquitto_path:
            # Try common installation paths
            possible_paths = [
                "/opt/homebrew/opt/mosquitto/sbin/mosquitto",
                "/usr/local/sbin/mosquitto",
                "/usr/sbin/mosquitto",
            ]
            for path in possible_paths:
                if shutil.which(path):
                    mosquitto_path = path
                    break

        if mosquitto_path:
            logger.info(f"Starting Mosquitto broker on port {port}...")
            try:
                # Start mosquitto in background
                subprocess.Popen(
                    [mosquitto_path, "-p", str(port)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                # Wait a bit for broker to start
                await asyncio.sleep(2)
                logger.info("Mosquitto broker started successfully")
                self._running = True  # Set running flag early
            except Exception as e:
                logger.warning(f"Failed to start Mosquitto: {e}")
                logger.info("Please start Mosquitto manually: mosquitto -p 1883")
        else:
            logger.warning("Mosquitto not found. Please install: brew install mosquitto")
            logger.info("Or start manually: mosquitto -p 1883")

    async def _publish_sensor(self, path: str, simulator: SensorSimulator):
        """Publish a single sensor update."""
        if self.client is None:
            return

        # Update sensor value
        value = simulator.update()

        # Split path into industry/sensor
        industry, sensor_name = path.split("/", 1)

        # Create topic
        topic_base = f"{self.config.topic_prefix}/{industry}/{sensor_name}"

        # Create payload based on format
        if self.config.payload_format == "json":
            payload = self._create_json_payload(simulator, value)
            payload_bytes = json.dumps(payload).encode("utf-8")
        elif self.config.payload_format == "sparkplug_b":
            payload_bytes = self._create_sparkplug_payload(simulator, value)
        else:  # string
            payload_bytes = str(value).encode("utf-8")

        # Publish to value topic
        await self.client.publish(
            f"{topic_base}/value",
            payload_bytes,
            qos=self.config.qos,
            retain=False,
        )

        # Optionally publish metadata (once per sensor, not every update)
        if self.config.include_metadata and self._message_count < len(self.simulators):
            metadata = self._create_metadata(simulator)
            await self.client.publish(
                f"{topic_base}/metadata",
                json.dumps(metadata).encode("utf-8"),
                qos=1,
                retain=True,  # Retain metadata
            )

    async def _publish_batch(self):
        """Publish all sensors in a single batch message."""
        if self.client is None:
            return

        batch = {}
        timestamp = int(time.time() * 1000)

        for path, simulator in self.simulators.items():
            value = simulator.update()
            industry, sensor_name = path.split("/", 1)

            if industry not in batch:
                batch[industry] = {}

            batch[industry][sensor_name] = {
                "value": value,
                "unit": simulator.config.unit,
                "type": simulator.config.sensor_type.value,
                "timestamp": timestamp,
            }

        # Publish batch
        topic = f"{self.config.topic_prefix}/batch"
        payload = json.dumps(batch, indent=None).encode("utf-8")

        await self.client.publish(
            topic,
            payload,
            qos=self.config.qos,
            retain=False,
        )

    def _create_json_payload(self, simulator: SensorSimulator, value: float) -> dict[str, Any]:
        """Create JSON payload for sensor value."""
        payload: dict[str, Any] = {
            "value": round(value, 3),
            "unit": simulator.config.unit,
        }

        if self.config.include_timestamp:
            payload["timestamp"] = int(time.time() * 1000)

        if self.config.include_metadata:
            payload.update(
                {
                    "sensor_type": simulator.config.sensor_type.value,
                    "min": simulator.config.min_value,
                    "max": simulator.config.max_value,
                    "nominal": simulator.config.nominal_value,
                }
            )

        # Add fault status if active
        if simulator.fault_active:
            payload["fault"] = True
            payload["fault_end"] = int(simulator.fault_end_time * 1000)

        return payload

    def _create_sparkplug_payload(self, simulator: SensorSimulator, value: float) -> bytes:
        """Create proper Sparkplug B payload using protobuf encoding."""
        if Device is None:
            # Fallback to JSON if pysparkplug not available
            logger.warning("pysparkplug not available, using JSON fallback")
            payload = {
                "timestamp": int(time.time() * 1000),
                "metrics": [
                    {
                        "name": simulator.config.name,
                        "timestamp": int(time.time() * 1000),
                        "datatype": "Double",
                        "value": round(value, 3),
                        "properties": {
                            "unit": simulator.config.unit,
                            "type": simulator.config.sensor_type.value,
                        },
                    }
                ],
                "seq": self._message_count,
            }
            return json.dumps(payload).encode("utf-8")

        # Create proper Sparkplug B protobuf message
        try:
            from pysparkplug.protobuf.sparkplug_b import Payload

            payload = Payload()
            payload.timestamp = int(time.time() * 1000)
            payload.seq = self._message_count

            # Add metric
            metric = payload.metrics.add()
            metric.name = simulator.config.name
            metric.timestamp = int(time.time() * 1000)
            metric.datatype = DataType.Double.value
            metric.double_value = round(value, 3)

            # Add properties for unit and type
            prop_unit = metric.properties.add()
            prop_unit.key = "unit"
            prop_unit.value.string_value = simulator.config.unit
            prop_unit.value.type = DataType.String.value

            prop_type = metric.properties.add()
            prop_type.key = "sensor_type"
            prop_type.value.string_value = simulator.config.sensor_type.value
            prop_type.value.type = DataType.String.value

            # Add fault status if active
            if simulator.fault_active:
                prop_fault = metric.properties.add()
                prop_fault.key = "fault"
                prop_fault.value.boolean_value = True
                prop_fault.value.type = DataType.Boolean.value

            return payload.SerializeToString()
        except Exception as e:
            logger.error(f"Error creating Sparkplug B payload: {e}, falling back to JSON")
            # Fallback to JSON on error
            payload_dict = {
                "timestamp": int(time.time() * 1000),
                "metrics": [
                    {
                        "name": simulator.config.name,
                        "timestamp": int(time.time() * 1000),
                        "datatype": "Double",
                        "value": round(value, 3),
                        "properties": {
                            "unit": simulator.config.unit,
                            "type": simulator.config.sensor_type.value,
                        },
                    }
                ],
                "seq": self._message_count,
            }
            return json.dumps(payload_dict).encode("utf-8")

    def _create_metadata(self, simulator: SensorSimulator) -> dict[str, Any]:
        """Create metadata payload for sensor."""
        return {
            "name": simulator.config.name,
            "sensor_type": simulator.config.sensor_type.value,
            "unit": simulator.config.unit,
            "min_value": simulator.config.min_value,
            "max_value": simulator.config.max_value,
            "nominal_value": simulator.config.nominal_value,
            "update_frequency_hz": simulator.config.update_frequency_hz,
            "cyclic": simulator.config.cyclic,
        }

    async def stop(self):
        """Stop the MQTT publisher."""
        self._running = False

    def inject_fault(self, sensor_path: str, duration: float = 10.0):
        """Inject a fault into a specific sensor."""
        if sensor_path in self.simulators:
            self.simulators[sensor_path].inject_fault(duration)
            logger.info(f"Fault injected into {sensor_path} for {duration} seconds")
        else:
            logger.warning(f"Sensor {sensor_path} not found")

    def get_stats(self) -> dict[str, Any]:
        """Get publisher statistics."""
        return {
            "message_count": self._message_count,
            "sensor_count": len(self.simulators),
            "running": self._running,
            "broker": f"{self.config.broker.host}:{self.config.broker.port}",
            "qos": self.config.qos,
            "format": self.config.payload_format,
        }


async def run_mqtt_simulator(config: MQTTConfig):
    """Run MQTT simulator (convenience function)."""
    sim = MQTTSimulator(config)
    await sim.start()


if __name__ == "__main__":
    import sys
    from ot_simulator.config_loader import load_config

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Load config
    config_path = sys.argv[1] if len(sys.argv) > 1 else "ot_simulator/config.yaml"
    full_config = load_config(config_path)

    # Run MQTT simulator
    asyncio.run(run_mqtt_simulator(full_config.mqtt))
