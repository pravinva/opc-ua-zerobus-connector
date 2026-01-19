"""Embedded MQTT broker using gmqtt (pure Python).

This broker runs in-process, eliminating the need for external Mosquitto.
Perfect for Databricks Apps deployment where system packages can't be installed.
"""

import asyncio
import logging
from typing import Optional

try:
    from gmqtt import Server as MQTTServer
    GMQTT_AVAILABLE = True
except ImportError:
    GMQTT_AVAILABLE = False
    MQTTServer = None

logger = logging.getLogger("ot_simulator.mqtt_broker")


class EmbeddedMQTTBroker:
    """Pure Python MQTT broker that runs embedded in the simulator process."""

    def __init__(self, host: str = "127.0.0.1", port: int = 1883):
        """
        Initialize embedded MQTT broker.

        Args:
            host: Host to bind to (default: 127.0.0.1)
            port: Port to bind to (default: 1883)
        """
        if not GMQTT_AVAILABLE:
            raise ImportError(
                "gmqtt package required for embedded broker. "
                "Install with: pip install gmqtt"
            )

        self.host = host
        self.port = port
        self.server: Optional[MQTTServer] = None
        self._running = False

    async def start(self):
        """Start the embedded MQTT broker."""
        if self._running:
            logger.warning("Broker already running")
            return

        try:
            self.server = MQTTServer()

            # Start listening
            await self.server.create_server(
                host=self.host,
                port=self.port
            )

            self._running = True
            logger.info(
                f"✓ Embedded MQTT broker started on {self.host}:{self.port}"
            )

        except Exception as e:
            logger.error(f"Failed to start MQTT broker: {e}")
            raise

    async def stop(self):
        """Stop the embedded MQTT broker."""
        if not self._running:
            return

        if self.server:
            self.server.close()
            self._running = False
            logger.info("Embedded MQTT broker stopped")

    async def run_forever(self):
        """Run the broker until stopped."""
        if not self._running:
            await self.start()

        # Keep running
        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            await self.stop()
            raise


# Fallback: Simple in-memory MQTT broker
class SimpleMQTTBroker:
    """Minimal MQTT broker for demo purposes when gmqtt not available."""

    def __init__(self, host: str = "127.0.0.1", port: int = 1883):
        self.host = host
        self.port = port
        self.subscribers = {}
        self._running = False

    async def start(self):
        """Start the simple broker."""
        self._running = True
        logger.warning(
            f"Using simplified MQTT broker on {self.host}:{self.port}. "
            "Install gmqtt for full functionality."
        )

    async def stop(self):
        """Stop the broker."""
        self._running = False

    def publish(self, topic: str, payload: bytes):
        """Publish a message (no-op for simple broker)."""
        pass


def create_embedded_broker(host: str = "127.0.0.1", port: int = 1883):
    """
    Create an embedded MQTT broker.

    Uses gmqtt if available, falls back to simple broker for demos.

    Args:
        host: Host to bind to
        port: Port to bind to

    Returns:
        EmbeddedMQTTBroker or SimpleMQTTBroker instance
    """
    if GMQTT_AVAILABLE:
        return EmbeddedMQTTBroker(host, port)
    else:
        logger.warning(
            "gmqtt not available. Using simplified broker. "
            "Install gmqtt for full MQTT functionality."
        )
        return SimpleMQTTBroker(host, port)
