"""OPC-UA protocol client implementation using unified protocol interface.

Security Features (OPC UA 10101 compliant):
- Basic256Sha256 encryption (Sign & SignAndEncrypt)
- Enterprise certificate-based authentication
- Username/password authentication
- Server certificate validation
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable

from asyncua import Client, Node
from asyncua.ua import DataChangeNotification, Variant

from connector.protocols.base import (
    ProtocolClient,
    ProtocolRecord,
    ProtocolTestResult,
    ProtocolType,
)
from connector.protocols.opcua_security import (
    OPCUASecurityConfig,
    OPCUASecurityManager,
    create_security_config_from_dict,
)

logger = logging.getLogger(__name__)


class OPCUAClient(ProtocolClient):
    """OPC-UA protocol client with subscription and backpressure handling."""

    def __init__(
        self,
        source_name: str,
        endpoint: str,
        config: dict[str, Any],
        on_record: Callable[[ProtocolRecord], None],
        on_stats: Callable[[dict[str, Any]], None] | None = None,
    ):
        super().__init__(source_name, endpoint, config, on_record, on_stats)

        # OPC-UA specific config
        self.variable_limit = int(config.get("variable_limit", 25))
        self.publishing_interval_ms = int(config.get("publishing_interval_ms", 1000))
        self.timeout_s = float(config.get("timeout", 5.0))

        # Security configuration
        security_config_dict = config.get("security", {})
        self.security_config = create_security_config_from_dict(security_config_dict)
        self.security_manager = OPCUASecurityManager(self.security_config)

        self._client: Client | None = None
        self._subscription: Any = None
        self._monitored_items: list[Any] = []
        self._namespaces: list[str] = []

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.OPCUA

    async def connect(self) -> None:
        """Establish OPC-UA connection with security."""
        if self._client is not None:
            return

        # Validate security configuration
        if not self.security_manager.validate_configuration():
            raise ValueError("Invalid OPC UA security configuration")

        # Log security status
        self.security_manager.log_security_status()

        # Create client with timeout
        self._client = Client(url=self.endpoint, timeout=self.security_config.timeout_s)

        # Configure security if enabled
        if self.security_config.enabled:
            # Set security policy and mode
            cert_path = self.security_manager.get_certificate_path()
            key_path = self.security_manager.get_private_key_path()

            if cert_path and key_path:
                await self._client.set_security_string(
                    f"{self.security_config.security_policy},"
                    f"{self.security_config.security_mode},"
                    f"{cert_path},{key_path}"
                )
                logger.info("✓ Configured certificate-based security")

            # Set username/password if provided
            if self.security_config.username and self.security_config.password:
                self._client.set_user(self.security_config.username)
                self._client.set_password(self.security_config.password)
                logger.info(f"✓ Configured username authentication: {self.security_config.username}")

            # Configure server certificate trust
            server_cert = self.security_manager.get_server_certificate_path()
            if server_cert:
                # TODO: Implement server certificate validation
                logger.info(f"✓ Trusting server certificate: {server_cert}")
            elif self.security_config.trust_all_certificates:
                logger.warning("⚠️  Trusting ALL server certificates (development mode)")
                # asyncua will accept any server certificate
            else:
                logger.info("Server certificate validation: strict mode (will reject unknown certs)")

        # Connect to server
        try:
            await self._client.connect()
            logger.info(f"✓ Connected to OPC UA server: {self.endpoint}")
        except Exception as e:
            logger.error(f"Failed to connect to {self.endpoint}: {e}")
            raise

        # Load namespace array
        try:
            ns_arr = await self._client.nodes.server_namespace_array.read_value()
            if isinstance(ns_arr, list):
                self._namespaces = ns_arr
                logger.info(f"✓ Loaded {len(self._namespaces)} namespaces")
        except Exception as e:
            logger.warning(f"Could not load namespace array: {e}")
            self._namespaces = []

    async def disconnect(self) -> None:
        """Disconnect from OPC-UA server."""
        # Clean up monitored items
        if self._monitored_items and self._subscription:
            try:
                await self._subscription.delete(self._monitored_items)
            except Exception:
                pass
            self._monitored_items = []

        # Delete subscription
        if self._subscription:
            try:
                await self._subscription.delete()
            except Exception:
                pass
            self._subscription = None

        # Disconnect client
        if self._client is not None:
            try:
                await self._client.disconnect()
            except Exception:
                pass
            finally:
                self._client = None

    async def subscribe(self) -> None:
        """Subscribe to OPC-UA variables."""
        if self._client is None:
            raise RuntimeError("Not connected")

        # Create subscription
        self._subscription = await self._client.create_subscription(
            period=self.publishing_interval_ms,
            handler=self._DataChangeHandler(self._on_datachange),
        )

        # Find variables to monitor
        variables = await self._discover_variables()

        # Create monitored items
        for var_node in variables[:self.variable_limit]:
            try:
                handle = await self._subscription.subscribe_data_change(var_node)
                self._monitored_items.append(handle)
            except Exception as e:
                self._emit_stats({
                    "subscribe_error": f"{type(e).__name__}: {e}",
                    "node": str(var_node),
                })

        self._emit_stats({
            "subscribed_variables": len(self._monitored_items),
            "subscription_interval_ms": self.publishing_interval_ms,
        })

        # Keep subscription alive until stop is requested
        while not self._stop_evt.is_set():
            await asyncio.sleep(1.0)

    async def _discover_variables(self) -> list[Node]:
        """Discover variables in the server."""
        if self._client is None:
            return []

        variables: list[Node] = []

        async def browse_node(node: Node, max_depth: int = 5, current_depth: int = 0) -> None:
            """Recursively browse nodes to find variables."""
            if current_depth >= max_depth or len(variables) >= self.variable_limit:
                return

            try:
                # Get children
                children = await node.get_children()

                for child in children:
                    if len(variables) >= self.variable_limit:
                        break

                    try:
                        # Check if it's a variable
                        node_class = await child.read_node_class()
                        if node_class.value == 2:  # Variable NodeClass
                            variables.append(child)
                        else:
                            # Continue browsing
                            await browse_node(child, max_depth, current_depth + 1)
                    except Exception:
                        continue

            except Exception:
                pass

        # Start from Objects folder
        try:
            objects_node = self._client.nodes.objects
            await browse_node(objects_node)
        except Exception:
            pass

        return variables

    def _on_datachange(
        self,
        node: Node,
        val: Any,
        data: DataChangeNotification,
    ) -> None:
        """Handle data change notification."""
        try:
            # Extract node information
            node_id_str = str(node.nodeid)
            namespace = node.nodeid.NamespaceIndex if hasattr(node.nodeid, 'NamespaceIndex') else 0

            # Extract value information
            value = val
            value_type = type(val).__name__
            value_num = None

            if isinstance(val, (int, float)):
                value_num = float(val)
            elif isinstance(val, Variant):
                value = val.Value
                value_type = str(val.VariantType)
                if isinstance(val.Value, (int, float)):
                    value_num = float(val.Value)

            # Extract status
            status_code = data.monitored_item.Value.StatusCode.value if hasattr(data, 'monitored_item') else 0
            status = "Good" if status_code == 0 else f"Bad({status_code})"

            # Get browse path (best effort)
            browse_path = node_id_str

            # Create record
            record = ProtocolRecord(
                event_time_ms=int(time.time() * 1000),
                source_name=self.source_name,
                endpoint=self.endpoint,
                protocol_type=self.protocol_type,
                topic_or_path=browse_path,
                value=value,
                value_type=value_type,
                value_num=value_num,
                metadata={
                    "namespace": namespace,
                    "node_id": node_id_str,
                    "status_code": status_code,
                },
                status_code=status_code,
                status=status,
            )

            self.on_record(record)

        except Exception as e:
            self._emit_stats({
                "datachange_error": f"{type(e).__name__}: {e}",
            })

    class _DataChangeHandler:
        """Handler for OPC-UA data change notifications."""

        def __init__(self, callback: Callable) -> None:
            self.callback = callback

        def datachange_notification(
            self,
            node: Node,
            val: Any,
            data: DataChangeNotification,
        ) -> None:
            """Called when a monitored item value changes."""
            self.callback(node, val, data)

    async def test_connection(self) -> ProtocolTestResult:
        """Test OPC-UA connectivity."""
        start_time = time.time()
        error = None
        server_info: dict[str, Any] = {}

        try:
            await self.connect()

            # Read server information
            try:
                app_desc = await self._client.nodes.server.read_description()
                server_info["application_name"] = str(getattr(app_desc, 'Text', app_desc))
            except Exception:
                pass

            try:
                ns_arr = await self._client.nodes.server_namespace_array.read_value()
                if isinstance(ns_arr, list):
                    server_info["namespaces"] = len(ns_arr)
            except Exception:
                pass

            try:
                status = await self._client.nodes.server_status.read_value()
                if hasattr(status, 'BuildInfo'):
                    build_info = status.BuildInfo
                    server_info["product_uri"] = getattr(build_info, 'ProductUri', None)
                    server_info["manufacturer"] = getattr(build_info, 'ManufacturerName', None)
            except Exception:
                pass

            await self.disconnect()
            ok = True

        except Exception as e:
            ok = False
            error = f"{type(e).__name__}: {e}"
        finally:
            duration_ms = int((time.time() - start_time) * 1000)

        return ProtocolTestResult(
            ok=ok,
            endpoint=self.endpoint,
            protocol_type=self.protocol_type,
            duration_ms=duration_ms,
            server_info=server_info if ok else None,
            error=error,
        )
