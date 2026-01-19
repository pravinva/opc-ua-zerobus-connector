"""
mDNS/Zeroconf Service Advertisement

Advertises OT simulator services (OPC UA, MQTT, Modbus) via mDNS/Zeroconf
for automatic network discovery.
"""

import logging
from typing import List, Optional
import socket

try:
    from zeroconf import ServiceInfo, Zeroconf
    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False

logger = logging.getLogger(__name__)


class MDNSAdvertiser:
    """Advertises industrial protocol services via mDNS/Zeroconf."""

    def __init__(self):
        """Initialize mDNS advertiser."""
        self.zeroconf: Optional[Zeroconf] = None
        self.services: List[ServiceInfo] = []
        self._running = False

        if not ZEROCONF_AVAILABLE:
            logger.warning("Zeroconf library not available - mDNS advertisement disabled")
            logger.info("Install with: pip install zeroconf")

    def start(self):
        """Start mDNS advertisement."""
        if not ZEROCONF_AVAILABLE:
            logger.debug("mDNS advertisement skipped (zeroconf not installed)")
            return

        try:
            self.zeroconf = Zeroconf()
            self._running = True
            logger.info("✓ mDNS advertiser started")
        except Exception as e:
            logger.error(f"Failed to start mDNS advertiser: {e}")

    def stop(self):
        """Stop mDNS advertisement and unregister all services."""
        if not self._running or not self.zeroconf:
            return

        logger.info("Unregistering mDNS services...")

        # Unregister all services
        for service in self.services:
            try:
                self.zeroconf.unregister_service(service)
                logger.debug(f"Unregistered {service.name}")
            except Exception as e:
                logger.warning(f"Error unregistering service: {e}")

        # Close zeroconf
        try:
            self.zeroconf.close()
        except Exception as e:
            logger.warning(f"Error closing zeroconf: {e}")

        self.services.clear()
        self._running = False
        logger.info("✓ mDNS advertiser stopped")

    def advertise_opcua(self, host: str = "127.0.0.1", port: int = 4840, name: str = "OT Simulator OPC UA"):
        """
        Advertise OPC UA server via mDNS.

        Args:
            host: Server host (default: 127.0.0.1)
            port: Server port (default: 4840)
            name: Service name for discovery
        """
        if not self._running or not self.zeroconf:
            return

        try:
            service_type = "_opcua-tcp._tcp.local."
            service_name = f"{name}.{service_type}"

            # Get local IP address
            local_ip = socket.gethostbyname(socket.gethostname())

            info = ServiceInfo(
                service_type,
                service_name,
                addresses=[socket.inet_aton(local_ip)],
                port=port,
                properties={
                    'path': '/ot-simulator/server/',
                    'version': '1.0',
                    'protocol': 'opcua',
                    'simulator': 'ot-simulator'
                },
                server=f"{socket.gethostname()}.local."
            )

            self.zeroconf.register_service(info)
            self.services.append(info)
            logger.info(f"✓ Advertising OPC UA service: {service_name} on {local_ip}:{port}")

        except Exception as e:
            logger.error(f"Failed to advertise OPC UA service: {e}")

    def advertise_mqtt(self, host: str = "127.0.0.1", port: int = 1883, tls: bool = False, name: str = "OT Simulator MQTT"):
        """
        Advertise MQTT broker via mDNS.

        Args:
            host: Broker host (default: 127.0.0.1)
            port: Broker port (default: 1883)
            tls: Whether TLS is enabled
            name: Service name for discovery
        """
        if not self._running or not self.zeroconf:
            return

        try:
            service_type = "_mqtts._tcp.local." if tls else "_mqtt._tcp.local."
            service_name = f"{name}.{service_type}"

            # Get local IP address
            local_ip = socket.gethostbyname(socket.gethostname())

            info = ServiceInfo(
                service_type,
                service_name,
                addresses=[socket.inet_aton(local_ip)],
                port=port,
                properties={
                    'version': '3.1.1',
                    'protocol': 'mqtt',
                    'tls': 'true' if tls else 'false',
                    'simulator': 'ot-simulator'
                },
                server=f"{socket.gethostname()}.local."
            )

            self.zeroconf.register_service(info)
            self.services.append(info)
            logger.info(f"✓ Advertising MQTT service: {service_name} on {local_ip}:{port}")

        except Exception as e:
            logger.error(f"Failed to advertise MQTT service: {e}")

    def advertise_modbus(self, host: str = "127.0.0.1", port: int = 502, name: str = "OT Simulator Modbus"):
        """
        Advertise Modbus TCP server via mDNS.

        Args:
            host: Server host (default: 127.0.0.1)
            port: Server port (default: 502)
            name: Service name for discovery
        """
        if not self._running or not self.zeroconf:
            return

        try:
            service_type = "_modbus._tcp.local."
            service_name = f"{name}.{service_type}"

            # Get local IP address
            local_ip = socket.gethostbyname(socket.gethostname())

            info = ServiceInfo(
                service_type,
                service_name,
                addresses=[socket.inet_aton(local_ip)],
                port=port,
                properties={
                    'protocol': 'modbus-tcp',
                    'version': '1.0',
                    'simulator': 'ot-simulator'
                },
                server=f"{socket.gethostname()}.local."
            )

            self.zeroconf.register_service(info)
            self.services.append(info)
            logger.info(f"✓ Advertising Modbus service: {service_name} on {local_ip}:{port}")

        except Exception as e:
            logger.error(f"Failed to advertise Modbus service: {e}")

    def is_available(self) -> bool:
        """Check if mDNS advertisement is available."""
        return ZEROCONF_AVAILABLE and self._running
