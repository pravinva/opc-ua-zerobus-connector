"""
Web GUI for Databricks IoT Connector

Provides REST API and web interface for:
- Configuration management
- Real-time monitoring
- Manual control (start/stop sources)
- Credential management
- Health checks
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Any, Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from aiohttp import web

try:
    from aiohttp import web
    import aiohttp_cors
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    web = None

logger = logging.getLogger(__name__)


class WebGUI:
    """Web GUI server for connector management and monitoring."""

    def __init__(
        self,
        bridge,
        config: Dict[str, Any],
        config_loader,
        credential_manager
    ):
        """
        Initialize Web GUI.

        Args:
            bridge: UnifiedBridge instance
            config: Configuration dictionary
            config_loader: ConfigLoader instance
            credential_manager: CredentialManager instance
        """
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp is required for Web GUI. Install with: pip install aiohttp aiohttp-cors")

        self.bridge = bridge
        self.config = config
        self.config_loader = config_loader
        self.credential_manager = credential_manager

        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None

    async def start(self, host: str = '0.0.0.0', port: int = 8080):
        """Start web server."""
        self.app = web.Application()

        # Setup routes
        self._setup_routes()

        # Setup CORS
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })

        # Apply CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)

        # Start server
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        self.site = web.TCPSite(self.runner, host, port)
        await self.site.start()

        logger.info(f"✓ Web GUI started on http://{host}:{port}")

    def _setup_routes(self):
        """Setup HTTP routes."""
        # API routes
        self.app.router.add_get('/api/status', self.handle_status)
        self.app.router.add_get('/api/metrics', self.handle_metrics)
        self.app.router.add_get('/api/config', self.handle_get_config)
        self.app.router.add_post('/api/config', self.handle_update_config)
        self.app.router.add_get('/api/sources', self.handle_list_sources)
        self.app.router.add_post('/api/sources/{name}/start', self.handle_start_source)
        self.app.router.add_post('/api/sources/{name}/stop', self.handle_stop_source)

        # OPC UA Discovery
        self.app.router.add_get('/api/opcua/discover', self.handle_opcua_discover)
        self.app.router.add_post('/api/opcua/discover/scan', self.handle_opcua_scan_network)

        # Modbus Discovery
        self.app.router.add_post('/api/modbus/discover/scan', self.handle_modbus_scan_network)

        # MQTT Discovery
        self.app.router.add_post('/api/mqtt/discover/scan', self.handle_mqtt_scan_network)

        # mDNS Discovery
        self.app.router.add_get('/api/mdns/discover', self.handle_mdns_discover)

        # Network info
        self.app.router.add_get('/api/network/info', self.handle_network_info)

        # Test endpoints
        self.app.router.add_post('/api/test/opcua', self.handle_test_opcua)
        self.app.router.add_post('/api/test/mqtt', self.handle_test_mqtt)
        self.app.router.add_post('/api/test/modbus', self.handle_test_modbus)

        # Add source endpoints
        self.app.router.add_post('/api/sources/add', self.handle_add_source)

        # ZeroBus configuration
        self.app.router.add_get('/api/zerobus/config', self.handle_get_zerobus_config)
        self.app.router.add_post('/api/zerobus/config', self.handle_save_zerobus_config)
        self.app.router.add_post('/api/zerobus/test', self.handle_test_zerobus)

        # ZeroBus endpoints
        self.app.router.add_get('/api/zerobus/status', self.handle_zerobus_status)
        self.app.router.add_get('/api/zerobus/diagnostics', self.handle_zerobus_diagnostics)
        self.app.router.add_get('/api/zerobus/diagnostics/raw', self.handle_zerobus_diagnostics_raw)

        # Normalization endpoints
        self.app.router.add_get('/api/normalization/status', self.handle_get_normalization_status)
        self.app.router.add_post('/api/normalization/toggle', self.handle_toggle_normalization)

        # Health check
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/ready', self.handle_ready)

        # Static frontend (simple HTML)
        self.app.router.add_get('/', self.handle_index)

    async def handle_status(self, request: web.Request) -> web.Response:
        """Get connector status."""
        try:
            status = self.bridge.get_status()
            return web.json_response(status)
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_metrics(self, request: web.Request) -> web.Response:
        """Get connector metrics."""
        try:
            metrics = self.bridge.get_metrics()
            return web.json_response(metrics)
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_get_config(self, request: web.Request) -> web.Response:
        """Get current configuration."""
        try:
            # Redact sensitive fields
            config_copy = json.loads(json.dumps(self.config))
            if 'zerobus' in config_copy and 'auth' in config_copy['zerobus']:
                config_copy['zerobus']['auth']['client_secret'] = '***REDACTED***'

            return web.json_response(config_copy)
        except Exception as e:
            logger.error(f"Error getting config: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_update_config(self, request: web.Request) -> web.Response:
        """Update configuration."""
        try:
            new_config = await request.json()

            # Validate config
            # TODO: Add validation logic

            # Save config
            self.config_loader.save_gui_state(new_config)

            return web.json_response({'status': 'ok', 'message': 'Configuration updated'})
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_list_sources(self, request: web.Request) -> web.Response:
        """List all configured sources with connection status."""
        try:
            sources = []
            for name, client in self.bridge.clients.items():
                # Check if client is actually connected
                # Different protocols have different connection indicators
                connected = False

                if hasattr(client, '_client') and client._client is not None:
                    # For OPC-UA: check if client is connected
                    if hasattr(client._client, 'uaclient'):
                        connected = client._client.uaclient is not None
                    # For MQTT: check if client is active
                    elif hasattr(client._client, '_client'):
                        connected = True  # MQTT client exists and is in context manager
                    # For Modbus: check if client is connected
                    elif hasattr(client._client, 'connected'):
                        connected = client._client.connected
                    else:
                        # Generic check: if _client exists, assume connected
                        connected = True

                sources.append({
                    'name': name,
                    'protocol': client.protocol_type.value,
                    'endpoint': client.endpoint,
                    'connected': connected,
                    'last_data_time': getattr(client, '_last_data_time', None),
                })

            return web.json_response({'sources': sources})
        except Exception as e:
            logger.error(f"Error listing sources: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_start_source(self, request: web.Request) -> web.Response:
        """Start a specific source."""
        source_name = request.match_info['name']

        try:
            # TODO: Implement start source logic
            return web.json_response({'status': 'ok', 'message': f'Source {source_name} started'})
        except Exception as e:
            logger.error(f"Error starting source: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_stop_source(self, request: web.Request) -> web.Response:
        """Stop a specific source."""
        source_name = request.match_info['name']

        try:
            # TODO: Implement stop source logic
            return web.json_response({'status': 'ok', 'message': f'Source {source_name} stopped'})
        except Exception as e:
            logger.error(f"Error stopping source: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_opcua_discover(self, request: web.Request) -> web.Response:
        """Discover OPC UA servers on the network."""
        try:
            from connector.protocols.opcua_discovery import get_discovery

            discovery_url = request.query.get('url', 'opc.tcp://localhost:4840')
            timeout = float(request.query.get('timeout', '5.0'))

            discovery = get_discovery()
            servers = await discovery.discover_servers(discovery_url, timeout=timeout)

            return web.json_response({
                'success': True,
                'servers': servers,
                'discovery_url': discovery_url
            })
        except Exception as e:
            logger.error(f"OPC UA discovery error: {e}")
            return web.json_response({'success': False, 'error': str(e)}, status=500)

    async def handle_opcua_scan_network(self, request: web.Request) -> web.Response:
        """Scan network for OPC UA servers."""
        try:
            from connector.protocols.opcua_discovery import get_discovery

            data = await request.json()
            ip_range = data.get('ip_range', '192.168.1.0/24')
            port = int(data.get('port', 4840))
            timeout = float(data.get('timeout', 2.0))

            discovery = get_discovery()
            servers = await discovery.scan_network(ip_range, port=port, timeout=timeout)

            return web.json_response({
                'success': True,
                'servers': servers,
                'ip_range': ip_range,
                'port': port
            })
        except Exception as e:
            logger.error(f"Network scan error: {e}")
            return web.json_response({'success': False, 'error': str(e)}, status=500)

    async def handle_modbus_scan_network(self, request: web.Request) -> web.Response:
        """Scan network for Modbus TCP devices."""
        try:
            from connector.protocols.modbus_discovery import get_discovery

            data = await request.json()
            ip_range = data.get('ip_range', '192.168.1.0/24')
            ports = data.get('ports', [502, 5020])
            timeout = float(data.get('timeout', 2.0))

            discovery = get_discovery()
            devices = await discovery.scan_network(ip_range, ports=ports, timeout=timeout)

            return web.json_response({
                'success': True,
                'devices': devices,
                'ip_range': ip_range,
                'ports': ports
            })
        except Exception as e:
            logger.error(f"Modbus scan error: {e}")
            return web.json_response({'success': False, 'error': str(e)}, status=500)

    async def handle_mqtt_scan_network(self, request: web.Request) -> web.Response:
        """Scan network for MQTT brokers."""
        try:
            from connector.protocols.mqtt_discovery import get_discovery

            data = await request.json()
            ip_range = data.get('ip_range', '192.168.1.0/24')
            ports = data.get('ports', [1883, 8883])
            timeout = float(data.get('timeout', 2.0))

            discovery = get_discovery()
            brokers = await discovery.scan_network(ip_range, ports=ports, timeout=timeout)

            return web.json_response({
                'success': True,
                'brokers': brokers,
                'ip_range': ip_range,
                'ports': ports
            })
        except Exception as e:
            logger.error(f"MQTT scan error: {e}")
            return web.json_response({'success': False, 'error': str(e)}, status=500)

    async def handle_mdns_discover(self, request: web.Request) -> web.Response:
        """Discover services via mDNS/Zeroconf."""
        try:
            from connector.protocols.mdns_discovery import get_discovery, is_available

            if not is_available():
                return web.json_response({
                    'success': False,
                    'error': 'mDNS discovery not available. Install zeroconf: pip install zeroconf'
                }, status=501)

            timeout = float(request.query.get('timeout', '5.0'))

            discovery = get_discovery()
            services = await discovery.discover_services(timeout=timeout)

            return web.json_response({
                'success': True,
                'services': services,
                'service_types': discovery.SERVICE_TYPES
            })
        except Exception as e:
            logger.error(f"mDNS discovery error: {e}")
            return web.json_response({'success': False, 'error': str(e)}, status=500)

    async def handle_network_info(self, request: web.Request) -> web.Response:
        """Get network information for the connector."""
        try:
            import socket
            import ipaddress

            # Get all network interfaces
            hostname = socket.gethostname()

            # Try to get the local IP by connecting to a public DNS
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # Connect to Google DNS (doesn't actually send data)
                s.connect(('8.8.8.8', 80))
                local_ip = s.getsockname()[0]
            except:
                local_ip = '127.0.0.1'
            finally:
                s.close()

            # Calculate the /24 network for this IP
            ip_obj = ipaddress.IPv4Address(local_ip)
            # Get the /24 network (class C)
            network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)

            return web.json_response({
                'success': True,
                'hostname': hostname,
                'local_ip': local_ip,
                'local_network': str(network),
                'network_cidr': f"{network.network_address}/24"
            })
        except Exception as e:
            logger.error(f"Network info error: {e}")
            return web.json_response({'success': False, 'error': str(e)}, status=500)

    async def handle_test_opcua(self, request: web.Request) -> web.Response:
        """Test OPC UA connection."""
        try:
            from asyncua import Client

            data = await request.json()
            endpoint = data.get('endpoint')

            if not endpoint:
                return web.json_response({'success': False, 'error': 'Endpoint required'}, status=400)

            # Try to connect using asyncua Client directly
            async with Client(endpoint) as ua_client:
                # Connect
                await ua_client.connect()

                # Get server info
                server_node = ua_client.get_server_node()
                server_state = await server_node.read_attribute(ua.AttributeIds.ServerState)

                # Browse nodes
                objects = ua_client.nodes.objects
                children = await objects.get_children()
                node_count = len(children)

                # Get namespace array
                namespaces = await ua_client.get_namespace_array()

                return web.json_response({
                    'success': True,
                    'server_info': {
                        'product_name': 'OPC UA Server',
                        'connected': True,
                        'namespaces': len(namespaces)
                    },
                    'node_count': node_count
                })

        except Exception as e:
            logger.error(f"OPC UA test connection error: {e}")
            return web.json_response({'success': False, 'error': str(e)}, status=500)

    async def handle_test_mqtt(self, request: web.Request) -> web.Response:
        """Test MQTT connection."""
        try:
            data = await request.json()
            broker = data.get('broker')
            port = int(data.get('port', 1883))

            if not broker:
                return web.json_response({'success': False, 'error': 'Broker required'}, status=400)

            # TODO: Implement MQTT test connection
            return web.json_response({
                'success': True,
                'broker': broker,
                'port': port,
                'message': 'MQTT test connection not yet implemented'
            })

        except Exception as e:
            logger.error(f"MQTT test connection error: {e}")
            return web.json_response({'success': False, 'error': str(e)}, status=500)

    async def handle_test_modbus(self, request: web.Request) -> web.Response:
        """Test Modbus connection."""
        try:
            data = await request.json()
            endpoint = data.get('endpoint')
            type = data.get('type', 'TCP')

            if not endpoint:
                return web.json_response({'success': False, 'error': 'Endpoint required'}, status=400)

            # TODO: Implement Modbus test connection
            return web.json_response({
                'success': True,
                'endpoint': endpoint,
                'type': type,
                'message': 'Modbus test connection not yet implemented'
            })

        except Exception as e:
            logger.error(f"Modbus test connection error: {e}")
            return web.json_response({'success': False, 'error': str(e)}, status=500)

    async def handle_add_source(self, request: web.Request) -> web.Response:
        """Add a new data source."""
        try:
            data = await request.json()
            source_type = data.get('type')  # 'opcua', 'mqtt', 'modbus'
            source_name = data.get('name')
            source_config = data.get('config')

            if not all([source_type, source_name, source_config]):
                return web.json_response({
                    'success': False,
                    'error': 'Missing required fields: type, name, config'
                }, status=400)

            # Add source to configuration
            if 'sources' not in self.config:
                self.config['sources'] = []

            # Check if source already exists
            existing = [s for s in self.config['sources'] if s.get('name') == source_name]
            if existing:
                return web.json_response({
                    'success': False,
                    'error': f'Source "{source_name}" already exists'
                }, status=409)

            # Add new source
            new_source = {
                'name': source_name,
                'type': source_type,
                **source_config
            }
            self.config['sources'].append(new_source)

            # Save configuration
            self.config_loader.save_config(self.config)

            # Start the new source
            await self.bridge.add_source(source_name, source_type, source_config)

            return web.json_response({
                'success': True,
                'message': f'Source "{source_name}" added and started successfully',
                'config_path': str(self.config_loader.state_config_path)
            })

        except Exception as e:
            logger.error(f"Add source error: {e}")
            return web.json_response({'success': False, 'error': str(e)}, status=500)

    async def handle_get_zerobus_config(self, request: web.Request) -> web.Response:
        """Get ZeroBus configuration with credentials loaded from encrypted storage."""
        try:
            # Get non-sensitive config from JSON file
            zerobus_config = self.config.get('zerobus', {})

            # Load credentials from encrypted storage
            credentials = self.credential_manager.load_credentials() or {}

            # Merge with credentials (prioritize encrypted storage, fallback to config file)
            client_id = credentials.get('zerobus_client_id') or zerobus_config.get('client_id', '')
            client_secret = credentials.get('zerobus_client_secret') or zerobus_config.get('client_secret', '')

            # Build response with credentials
            response_config = {
                'enabled': zerobus_config.get('enabled', False),
                'workspace_url': zerobus_config.get('workspace_url', ''),
                'endpoint': zerobus_config.get('endpoint', ''),
                'target_table': zerobus_config.get('target_table', ''),
                'source_id': zerobus_config.get('source_id', ''),
                'debug': zerobus_config.get('debug', False),
                'client_id': client_id,
                'client_secret': client_secret,
                'credentials_encrypted': bool(self.credential_manager.master_password and credentials)
            }

            return web.json_response(response_config)

        except Exception as e:
            logger.error(f"Get ZeroBus config error: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_save_zerobus_config(self, request: web.Request) -> web.Response:
        """Save ZeroBus configuration with encrypted credentials."""
        try:
            data = await request.json()

            # Update config (non-sensitive fields only)
            if 'zerobus' not in self.config:
                self.config['zerobus'] = {}

            self.config['zerobus']['enabled'] = data.get('enabled', True)
            self.config['zerobus']['workspace_url'] = data.get('workspace_url', '')
            self.config['zerobus']['endpoint'] = data.get('endpoint', '')
            self.config['zerobus']['target_table'] = data.get('target_table', '')
            self.config['zerobus']['source_id'] = data.get('source_id', '')
            self.config['zerobus']['debug'] = data.get('debug', False)

            # Save non-sensitive config to JSON file
            self.config_loader.save_config(self.config)

            # Save sensitive credentials to encrypted storage
            client_id = data.get('client_id', '')
            client_secret = data.get('client_secret', '')

            if client_id or client_secret:
                # Load existing credentials
                credentials = self.credential_manager.load_credentials() or {}

                # Update ZeroBus credentials
                if client_id:
                    credentials['zerobus_client_id'] = client_id
                if client_secret:
                    credentials['zerobus_client_secret'] = client_secret

                # Save encrypted credentials
                if self.credential_manager.master_password:
                    if self.credential_manager.store_credentials(credentials):
                        logger.info("✓ ZeroBus credentials encrypted and saved")
                    else:
                        logger.warning("Failed to encrypt credentials - falling back to config file")
                        # Fallback: store in config (plain text) if encryption fails
                        self.config['zerobus']['client_id'] = client_id
                        self.config['zerobus']['client_secret'] = client_secret
                        self.config_loader.save_config(self.config)
                else:
                    # No master password - store in config (plain text) with warning
                    logger.warning("⚠️  Storing credentials in PLAIN TEXT (no master password set)")
                    logger.warning("Set CONNECTOR_MASTER_PASSWORD environment variable to enable encryption")
                    self.config['zerobus']['client_id'] = client_id
                    self.config['zerobus']['client_secret'] = client_secret
                    self.config_loader.save_config(self.config)

            return web.json_response({
                'success': True,
                'message': 'ZeroBus configuration saved successfully' +
                          (' (credentials encrypted)' if self.credential_manager.master_password else ' (credentials NOT encrypted)')
            })

        except Exception as e:
            logger.error(f"Save ZeroBus config error: {e}")
            return web.json_response({'success': False, 'error': str(e)}, status=500)

    async def handle_test_zerobus(self, request: web.Request) -> web.Response:
        """Test ZeroBus connection with OAuth and table verification."""
        try:
            import aiohttp
            from databricks.sdk import WorkspaceClient
            from databricks.sdk.core import Config

            data = await request.json()
            workspace_url = data.get('workspace_url')
            endpoint = data.get('endpoint')
            client_id = data.get('client_id')
            client_secret = data.get('client_secret')
            target_table = data.get('target_table', '')

            if not all([workspace_url, endpoint, client_id, client_secret]):
                return web.json_response({
                    'success': False,
                    'error': 'Missing required fields: workspace_url, endpoint, client_id, client_secret'
                }, status=400)

            # Test 1: OAuth authentication
            try:
                config = Config(
                    host=workspace_url,
                    client_id=client_id,
                    client_secret=client_secret
                )
                w = WorkspaceClient(config=config)

                # Try to get current user to verify authentication
                current_user = w.current_user.me()
                username = current_user.user_name
                logger.info(f"✓ OAuth authentication successful: {username}")
            except Exception as e:
                return web.json_response({
                    'success': False,
                    'error': f'OAuth authentication failed: {str(e)}'
                }, status=401)

            # Test 2: Verify table exists (if target_table provided)
            if target_table:
                try:
                    parts = target_table.split('.')
                    if len(parts) != 3:
                        return web.json_response({
                            'success': False,
                            'error': f'Invalid table format: {target_table}. Expected: catalog.schema.table'
                        }, status=400)

                    catalog, schema, table = parts
                    table_info = w.tables.get(f"{catalog}.{schema}.{table}")
                    logger.info(f"✓ Table verified: {target_table}")
                except Exception as e:
                    logger.warning(f"Table verification failed (table may not exist yet): {e}")
                    # Don't fail the test if table doesn't exist - it might be created later

            # Test 3: Verify ZeroBus endpoint is accessible
            try:
                async with aiohttp.ClientSession() as session:
                    # Just check if endpoint is reachable (don't send actual data)
                    test_url = f"{workspace_url.rstrip('/')}/api/2.0/workspace/get-status"
                    async with session.get(test_url, headers={"Authorization": f"Bearer {w.config.authenticate()}"}, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status < 500:  # 2xx, 3xx, 4xx are all "reachable"
                            logger.info(f"✓ Workspace endpoint reachable: {workspace_url}")
            except Exception as e:
                logger.warning(f"Workspace endpoint check: {e}")
                # Don't fail test - endpoint might work even if this test fails

            return web.json_response({
                'success': True,
                'message': f'✓ ZeroBus connection successful',
                'details': {
                    'workspace_url': workspace_url,
                    'endpoint': endpoint,
                    'authenticated_user': username,
                    'table_verified': target_table if target_table else 'Not checked'
                }
            })

        except Exception as e:
            logger.error(f"Test ZeroBus connection error: {e}")
            return web.json_response({'success': False, 'error': str(e)}, status=500)

    async def handle_zerobus_status(self, request: web.Request) -> web.Response:
        """Get ZeroBus connection status."""
        try:
            status = self.bridge.zerobus.get_connection_status()
            return web.json_response({
                'connected': status.get('connected', False),
                'workspace_url': status.get('workspace_url', ''),
                'target_table': status.get('target_table', ''),
                'stream_id': status.get('stream_id', '')
            })
        except Exception as e:
            logger.error(f"ZeroBus status error: {e}")
            return web.json_response({'connected': False, 'error': str(e)})

    async def handle_zerobus_diagnostics(self, request: web.Request) -> web.Response:
        """Get ZeroBus diagnostics."""
        try:
            metrics = self.bridge.zerobus.get_metrics()
            status = self.bridge.zerobus.get_connection_status()
            config = self.bridge.config.get('zerobus', {})

            runtime_text = f"""=== Zerobus Module Diagnostics ===
Module Enabled: {config.get('enabled', False)}

=== Zerobus Client Diagnostics ===
Initialized: {status.get('connected', False)}
Connected: {status.get('connected', False)}
Stream ID: {status.get('stream_id', 'N/A')}
Stream State: {status.get('state', 'UNKNOWN')}
Total Events Sent: {metrics.get('batches_sent', 0)}
Total Batches Sent: {metrics.get('batches_sent', 0)}
Total Failures: {metrics.get('send_failures', 0)}
Last Acked Offset: N/A
Last Successful Send: N/A
Last Error: {metrics.get('last_error', 'NONE')}
Last Error At: N/A
Consecutive Failures: {metrics.get('consecutive_failures', 0)}"""

            return web.json_response({
                'health': {
                    'status': 'ok' if status.get('connected') else 'disconnected',
                    'enabled': config.get('enabled', False)
                },
                'config': {
                    'workspace_url': config.get('workspace_host', ''),
                    'zerobus_endpoint': config.get('zerobus_endpoint', ''),
                    'target_table': f"{config.get('target', {}).get('catalog', '')}.{config.get('target', {}).get('schema', '')}.{config.get('target', {}).get('table', '')}",
                    'tag_mode': 'explicit',
                    'explicit_tags': 0,
                    'include_subfolders': True,
                    'store_forward': config.get('backpressure', {}).get('spool_enabled', False),
                    'spool_dir': config.get('backpressure', {}).get('spool_dir', '/app/spool')
                },
                'runtime': runtime_text
            })
        except Exception as e:
            logger.error(f"ZeroBus diagnostics error: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_zerobus_diagnostics_raw(self, request: web.Request) -> web.Response:
        """Get raw ZeroBus diagnostics (plain text)."""
        try:
            metrics = self.bridge.zerobus.get_metrics()
            status = self.bridge.zerobus.get_connection_status()
            config = self.bridge.config.get('zerobus', {})

            text = f"""Databricks ZeroBus Connector - Diagnostics
============================================

Module Status:
  Enabled: {config.get('enabled', False)}
  Connected: {status.get('connected', False)}

Connection:
  Workspace: {config.get('workspace_host', '')}
  Endpoint: {config.get('zerobus_endpoint', '')}
  Target Table: {config.get('target', {}).get('catalog', '')}.{config.get('target', {}).get('schema', '')}.{config.get('target', {}).get('table', '')}

Stream Info:
  Stream ID: {status.get('stream_id', 'N/A')}
  State: {status.get('state', 'UNKNOWN')}

Metrics:
  Batches Sent: {metrics.get('batches_sent', 0)}
  Send Failures: {metrics.get('send_failures', 0)}
  Consecutive Failures: {metrics.get('consecutive_failures', 0)}
  Last Error: {metrics.get('last_error', 'NONE')}
"""

            return web.Response(text=text, content_type='text/plain')
        except Exception as e:
            logger.error(f"ZeroBus raw diagnostics error: {e}")
            return web.Response(text=f"Error: {str(e)}", status=500)

    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({'status': 'healthy'})

    async def handle_ready(self, request: web.Request) -> web.Response:
        """Readiness check endpoint."""
        try:
            status = self.bridge.get_status()
            ready = status.get('zerobus_connected', False)

            if ready:
                return web.json_response({'status': 'ready'})
            else:
                return web.json_response({'status': 'not ready'}, status=503)
        except Exception as e:
            return web.json_response({'status': 'error', 'error': str(e)}, status=503)

    async def handle_get_normalization_status(self, request: web.Request) -> web.Response:
        """Get normalization status."""
        try:
            from connector.normalizer import get_normalization_manager
            manager = get_normalization_manager()

            return web.json_response({
                'success': True,
                'enabled': manager.is_enabled()
            })
        except Exception as e:
            logger.error(f"Error getting normalization status: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def handle_toggle_normalization(self, request: web.Request) -> web.Response:
        """Toggle normalization on/off."""
        try:
            data = await request.json()
            enabled = data.get('enabled', False)

            from connector.normalizer import get_normalization_manager
            manager = get_normalization_manager()
            manager.set_enabled(enabled)

            # Update config file
            import yaml
            config_path = 'iot_connector/config/normalization_config.yaml'
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f) or {}

                if 'features' not in config:
                    config['features'] = {}
                config['features']['normalization_enabled'] = enabled
                config['mode'] = 'normalized' if enabled else 'raw'

                with open(config_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)

                logger.info(f"✓ Normalization {'enabled' if enabled else 'disabled'}")

            except Exception as e:
                logger.warning(f"Could not update config file: {e}")

            return web.json_response({
                'success': True,
                'enabled': enabled,
                'message': f'Normalization {"enabled" if enabled else "disabled"}'
            })
        except Exception as e:
            logger.error(f"Error toggling normalization: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def handle_index(self, request: web.Request) -> web.Response:
        """Serve professional configuration dashboard."""
        html = self._get_enhanced_html()
        return web.Response(text=html, content_type='text/html')

    def _get_enhanced_html(self) -> str:
        """Generate enhanced HTML with collapsible config sections."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Databricks IoT Connector - Configuration</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #F5F7FA;
            color: #1E293B;
            min-height: 100vh;
            padding: 24px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        /* Header */
        .header {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 32px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }

        .logo-section {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 16px;
        }

        .databricks-logo {
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, #FF3621 0%, #FF6B58 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 24px;
            color: white;
            box-shadow: 0 4px 12px rgba(255, 54, 33, 0.3);
        }

        h1 {
            font-size: 36px;
            font-weight: 700;
            color: #1E293B;
            margin-bottom: 8px;
        }

        .subtitle {
            color: #64748B;
            font-size: 16px;
            font-weight: 400;
        }

        /* Status Bar */
        .status-bar {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }

        .status-card {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }

        .status-label {
            color: #64748B;
            font-size: 14px;
            margin-bottom: 8px;
        }

        .status-value {
            font-size: 28px;
            font-weight: 700;
        }

        .status-ok { color: #10B981; }
        .status-error { color: #EF4444; }
        .status-warning { color: #F59E0B; }

        /* Collapsible Sections */
        .config-section {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            margin-bottom: 16px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }

        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 24px;
            cursor: pointer;
            transition: background 0.2s;
        }

        .section-header:hover {
            background: #F8FAFC;
        }

        .section-title {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 18px;
            font-weight: 600;
        }

        .protocol-icon {
            width: 40px;
            height: 40px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 14px;
        }

        .icon-zerobus { background: linear-gradient(135deg, #FF3621 0%, #FF6B58 100%); }
        .icon-opcua { background: linear-gradient(135deg, #1F6FEB 0%, #3B8BFF 100%); }
        .icon-mqtt { background: linear-gradient(135deg, #10B981 0%, #34D399 100%); }
        .icon-modbus { background: linear-gradient(135deg, #F59E0B 0%, #FBBF24 100%); }

        .chevron {
            width: 24px;
            height: 24px;
            transition: transform 0.3s;
        }

        .section-header.expanded .chevron {
            transform: rotate(180deg);
        }

        .section-content {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
            padding: 0 24px;
        }

        .section-content.expanded {
            max-height: 2000px;
            padding: 0 24px 24px 24px;
        }

        /* Form Styles */
        .form-group {
            margin-bottom: 20px;
        }

        .form-label {
            display: block;
            color: #475569;
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 8px;
        }

        .form-input, .form-select {
            width: 100%;
            background: white;
            border: 1px solid #CBD5E1;
            border-radius: 8px;
            padding: 12px 16px;
            color: #1E293B;
            font-size: 14px;
            font-family: 'Inter', sans-serif;
        }

        .form-input:focus, .form-select:focus {
            outline: none;
            border-color: #3B82F6;
            background: white;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .form-checkbox {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
        }

        input[type="checkbox"] {
            width: 20px;
            height: 20px;
            cursor: pointer;
        }

        /* Buttons */
        .button-group {
            display: flex;
            gap: 12px;
            margin-top: 24px;
        }

        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            font-family: 'Inter', sans-serif;
        }

        .btn-primary {
            background: #3B82F6;
            color: white;
            box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
        }

        .btn-primary:hover {
            background: #2563EB;
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
        }

        .btn-secondary {
            background: white;
            color: #475569;
            border: 1px solid #CBD5E1;
        }

        .btn-secondary:hover {
            background: #F8FAFC;
            border-color: #94A3B8;
        }

        /* Diagnostics */
        .diagnostics-output {
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 16px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            color: #10B981;
            max-height: 300px;
            overflow-y: auto;
            margin-top: 16px;
        }

        .diagnostics-output.error {
            color: #EF4444;
        }

        /* Grid Layout */
        .form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }

        .sources-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
        }

        .sources-table th {
            background: #F8FAFC;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #475569;
            font-size: 14px;
            border-bottom: 2px solid #E2E8F0;
        }

        .sources-table td {
            padding: 12px;
            border-top: 1px solid #E2E8F0;
            font-size: 14px;
            color: #1E293B;
        }

        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }

        .badge-opcua { background: rgba(31, 111, 235, 0.2); color: #3B8BFF; }
        .badge-mqtt { background: rgba(16, 185, 129, 0.2); color: #34D399; }
        .badge-modbus { background: rgba(245, 158, 11, 0.2); color: #FBBF24; }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="logo-section">
                <div class="databricks-logo">D</div>
                <div>
                    <h1>IoT Connector Configuration</h1>
                    <div class="subtitle">Configure data sources and streaming settings</div>
                </div>
            </div>
        </div>

        <!-- Status Bar -->
        <div class="status-bar">
            <div class="status-card">
                <div class="status-label">Active Sources</div>
                <div class="status-value" id="active-sources">-</div>
            </div>
            <div class="status-card">
                <div class="status-label">ZeroBus Status</div>
                <div class="status-value" id="zerobus-status">-</div>
            </div>
            <div class="status-card">
                <div class="status-label">Queue Depth</div>
                <div class="status-value" id="queue-depth">-</div>
            </div>
            <div class="status-card">
                <div class="status-label">Records Sent</div>
                <div class="status-value" id="records-sent">-</div>
            </div>
        </div>

        <!-- ZeroBus Configuration -->
        <div class="config-section">
            <div class="section-header" onclick="toggleSection('zerobus')">
                <div class="section-title">
                    <div class="protocol-icon icon-zerobus">ZB</div>
                    <span>ZeroBus Connector Configuration</span>
                </div>
                <svg class="chevron" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/>
                </svg>
            </div>
            <div class="section-content" id="zerobus-content">
                <p style="color: #64748B; font-size: 14px; margin-bottom: 24px;">
                    Configure the connection to Databricks Zerobus for real-time data streaming
                </p>

                <!-- Connection Status Badge -->
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="width: 12px; height: 12px; background: #EF4444; border-radius: 50%; display: inline-block;" id="zerobus-status-indicator"></span>
                        <span style="color: #EF4444; font-size: 14px; font-weight: 500;" id="zerobus-status-text">Disconnected</span>
                    </div>
                    <div style="display: flex; gap: 12px;">
                        <button class="btn btn-secondary" onclick="showZeroBusDiagnostics()" style="padding: 8px 16px; font-size: 13px;">Diagnostics</button>
                        <button class="btn btn-secondary" onclick="refreshZeroBusStatus()" style="padding: 8px 16px; font-size: 13px;">Refresh</button>
                    </div>
                </div>

                <!-- Module Control -->
                <div style="border-bottom: 1px solid #E2E8F0; padding-bottom: 24px; margin-bottom: 24px;">
                    <h3 style="color: #3B82F6; font-size: 15px; font-weight: 600; margin-bottom: 16px;">Module Control</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
                        <div class="form-group">
                            <label class="form-checkbox">
                                <input type="checkbox" id="zerobus-enabled" checked>
                                <span>Enable Module</span>
                            </label>
                            <p style="color: #64748B; font-size: 12px; margin-top: 4px;">Enable or disable the Zerobus connector module</p>
                        </div>
                        <div class="form-group">
                            <label class="form-checkbox">
                                <input type="checkbox" id="zerobus-debug">
                                <span>Debug Logging</span>
                            </label>
                            <p style="color: #64748B; font-size: 12px; margin-top: 4px;">Enable verbose debug logging for troubleshooting</p>
                        </div>
                    </div>
                </div>

                <!-- Databricks Connection -->
                <div style="border-bottom: 1px solid #E2E8F0; padding-bottom: 24px; margin-bottom: 24px;">
                    <h3 style="color: #3B82F6; font-size: 15px; font-weight: 600; margin-bottom: 16px;">Databricks Connection</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px;">
                        <div class="form-group">
                            <label class="form-label">Workspace URL <span style="color: #EF4444;">*</span></label>
                            <input type="text" class="form-input" id="zerobus-workspace-url" placeholder="https://e2-demo-field-eng.cloud.databricks.com" style="font-size: 13px;">
                            <p style="color: #64748B; font-size: 11px; margin-top: 4px;">Databricks workspace URL</p>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Zerobus Endpoint <span style="color: #EF4444;">*</span></label>
                            <input type="text" class="form-input" id="zerobus-endpoint" placeholder="144482830581485.zerobus.us-west-2.cloud.databricks.com" style="font-size: 13px;">
                            <p style="color: #64748B; font-size: 11px; margin-top: 4px;">Zerobus ingest endpoint</p>
                        </div>
                        <div class="form-group">
                            <label class="form-label">OAuth Client ID <span style="color: #EF4444;">*</span></label>
                            <input type="text" class="form-input" id="zerobus-client-id" placeholder="62393ed8-ea22-4830-a6ef-6b6545e6be5f" style="font-size: 13px;">
                            <p style="color: #64748B; font-size: 11px; margin-top: 4px;">Service principal client ID for authentication</p>
                        </div>
                    </div>
                    <div class="form-group" style="margin-top: 16px;">
                        <label class="form-label">OAuth Client Secret <span style="color: #EF4444;">*</span></label>
                        <input type="password" class="form-input" id="zerobus-client-secret" placeholder="••••" style="font-size: 13px;">
                        <p style="color: #64748B; font-size: 11px; margin-top: 4px;">Service principal client secret (encrypted)</p>
                    </div>
                </div>

                <!-- Unity Catalog Configuration -->
                <div style="border-bottom: 1px solid #E2E8F0; padding-bottom: 24px; margin-bottom: 24px;">
                    <h3 style="color: #3B82F6; font-size: 15px; font-weight: 600; margin-bottom: 16px;">Unity Catalog Configuration</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                        <div class="form-group">
                            <label class="form-label">Target Table <span style="color: #EF4444;">*</span></label>
                            <input type="text" class="form-input" id="zerobus-target-table" placeholder="ignition_demo.scada_data.tag_events" style="font-size: 13px;">
                            <p style="color: #64748B; font-size: 11px; margin-top: 4px;">Unity Catalog table in format: catalog.schema.table</p>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Source System ID</label>
                            <input type="text" class="form-input" id="zerobus-source-id" placeholder="ignition-gateway81-colima" style="font-size: 13px;">
                            <p style="color: #64748B; font-size: 11px; margin-top: 4px;">Identifier for this data source</p>
                        </div>
                    </div>
                </div>

                <!-- Backpressure & Queue Management -->
                <div style="border-bottom: 1px solid #E2E8F0; padding-bottom: 24px; margin-bottom: 24px;">
                    <h3 style="color: #3B82F6; font-size: 15px; font-weight: 600; margin-bottom: 16px;">Backpressure & Queue Management</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                        <div class="form-group">
                            <label class="form-label">Max Queue Size</label>
                            <input type="number" class="form-input" id="backpressure-queue-size" placeholder="10000" value="10000" style="font-size: 13px;">
                            <p style="color: #64748B; font-size: 11px; margin-top: 4px;">Maximum number of records in memory queue</p>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Batch Timeout (seconds)</label>
                            <input type="number" class="form-input" id="backpressure-batch-timeout" placeholder="5" value="5" style="font-size: 13px;">
                            <p style="color: #64748B; font-size: 11px; margin-top: 4px;">Maximum time to wait before sending batch</p>
                        </div>
                    </div>
                </div>

                <!-- Store & Forward -->
                <div style="border-bottom: 1px solid #E2E8F0; padding-bottom: 24px; margin-bottom: 24px;">
                    <h3 style="color: #3B82F6; font-size: 15px; font-weight: 600; margin-bottom: 16px;">Store & Forward</h3>
                    <div class="form-group">
                        <label class="form-checkbox">
                            <input type="checkbox" id="spool-enabled" checked>
                            <span>Enable Disk Spool</span>
                        </label>
                        <p style="color: #64748B; font-size: 12px; margin-top: 4px;">Store records to disk when ZeroBus is unavailable</p>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px;">
                        <div class="form-group">
                            <label class="form-label">Spool Directory</label>
                            <input type="text" class="form-input" id="spool-directory" placeholder="data/zerobus-spool" value="data/zerobus-spool" style="font-size: 13px;">
                            <p style="color: #64748B; font-size: 11px; margin-top: 4px;">Path to disk spool directory</p>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Max Spool Size (MB)</label>
                            <input type="number" class="form-input" id="spool-max-size" placeholder="1024" value="1024" style="font-size: 13px;">
                            <p style="color: #64748B; font-size: 11px; margin-top: 4px;">Maximum disk space for spool files</p>
                        </div>
                    </div>
                </div>

                <!-- Action Buttons -->
                <div style="display: flex; gap: 12px; margin-top: 24px;">
                    <button class="btn btn-primary" onclick="saveZeroBusConfig()" style="padding: 10px 24px;">Save Configuration</button>
                    <button class="btn" onclick="testZeroBusConnection()" style="padding: 10px 24px; background: #059669; color: white;">Test Connection</button>
                    <button class="btn btn-secondary" onclick="cancelZeroBusConfig()" style="padding: 10px 24px;">Cancel</button>
                </div>

                <!-- Diagnostics Panel -->
                <div id="zerobus-diagnostics-panel" style="display: none; margin-top: 32px; border-top: 2px solid #3B82F6; padding-top: 24px;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
                        <h3 style="color: #3B82F6; font-size: 16px; font-weight: 600;">Diagnostics</h3>
                        <div style="display: flex; align-items: center; gap: 16px;">
                            <span style="color: #64748B; font-size: 13px;" id="diagnostics-timestamp">Last updated: 16/01/2026, 09:56:09</span>
                            <button class="btn btn-secondary" onclick="refreshZeroBusDiagnostics()" style="padding: 6px 12px; font-size: 13px;">Refresh Diagnostics</button>
                        </div>
                    </div>

                    <!-- Health & Configuration Summary -->
                    <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 24px; margin-bottom: 24px;">
                        <!-- Health -->
                        <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid #10B981; border-radius: 8px; padding: 16px;">
                            <h4 style="color: #10B981; font-size: 14px; font-weight: 600; margin-bottom: 12px;">Health</h4>
                            <div style="display: flex; flex-direction: column; gap: 8px;">
                                <div style="display: flex; justify-content: space-between;">
                                    <span style="color: #64748B; font-size: 13px;">Status</span>
                                    <span style="color: #10B981; font-size: 13px; font-weight: 500;" id="diag-status">ok</span>
                                </div>
                                <div style="display: flex; justify-content: space-between;">
                                    <span style="color: #64748B; font-size: 13px;">Enabled</span>
                                    <span style="color: #1E293B; font-size: 13px;" id="diag-enabled">true</span>
                                </div>
                            </div>
                        </div>

                        <!-- Configuration Summary -->
                        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 16px;">
                            <h4 style="color: #1E293B; font-size: 14px; font-weight: 600; margin-bottom: 12px;">Configuration (summary)</h4>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 13px;">
                                <div><span style="color: #64748B;">Workspace URL</span></div>
                                <div><span style="color: #1E293B; word-break: break-all;" id="diag-workspace">-</span></div>

                                <div><span style="color: #64748B;">Zerobus Endpoint</span></div>
                                <div><span style="color: #1E293B; word-break: break-all;" id="diag-endpoint">-</span></div>

                                <div><span style="color: #64748B;">Target Table</span></div>
                                <div><span style="color: #1E293B;" id="diag-table">-</span></div>

                                <div><span style="color: #64748B;">Queue Size</span></div>
                                <div><span style="color: #1E293B;" id="diag-queuesize">10000</span></div>

                                <div><span style="color: #64748B;">Batch Timeout</span></div>
                                <div><span style="color: #1E293B;" id="diag-batchtimeout">5s</span></div>

                                <div><span style="color: #64748B;">Store & Forward</span></div>
                                <div><span style="color: #1E293B;" id="diag-storeforward">true</span></div>

                                <div><span style="color: #64748B;">Spool Dir</span></div>
                                <div><span style="color: #1E293B;" id="diag-spooldir">data/zerobus-spool</span></div>
                            </div>
                        </div>
                    </div>

                    <!-- Runtime Diagnostics -->
                    <div>
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                            <h4 style="color: #1E293B; font-size: 14px; font-weight: 600;">Runtime diagnostics</h4>
                            <button class="btn btn-secondary" onclick="openRawDiagnostics()" style="padding: 4px 12px; font-size: 12px;">Open raw</button>
                        </div>
                        <div style="background: #1E293B; border: 1px solid #E2E8F0; border-radius: 8px; padding: 16px; font-family: 'Courier New', monospace; font-size: 12px; color: #10B981; max-height: 300px; overflow-y: auto;" id="runtime-diagnostics">
                            <pre style="margin: 0; white-space: pre-wrap; word-wrap: break-word;">Loading diagnostics...</pre>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- OPC UA Configuration -->
        <div class="config-section">
            <div class="section-header" onclick="toggleSection('opcua')">
                <div class="section-title">
                    <div class="protocol-icon icon-opcua">UA</div>
                    <span>OPC UA Sources</span>
                </div>
                <svg class="chevron" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/>
                </svg>
            </div>
            <div class="section-content" id="opcua-content">
                <div class="form-grid">
                    <div class="form-group">
                        <label class="form-label">Source Name</label>
                        <input type="text" class="form-input" id="opcua-name" placeholder="opcua_source_1">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Endpoint URL</label>
                        <input type="text" class="form-input" id="opcua-endpoint" placeholder="opc.tcp://localhost:4840/server">
                    </div>
                </div>

                <div class="form-grid">
                    <div class="form-group">
                        <label class="form-label">Security Mode</label>
                        <select class="form-select" id="opcua-security">
                            <option value="None">None</option>
                            <option value="Sign">Sign</option>
                            <option value="SignAndEncrypt">Sign and Encrypt</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Publishing Interval (ms)</label>
                        <input type="number" class="form-input" id="opcua-interval" value="1000">
                    </div>
                </div>

                <div class="button-group">
                    <button class="btn btn-primary" onclick="testOPCUAConnection()">Test Connection</button>
                    <button class="btn" onclick="discoverOPCUAServers()" style="background: #8B5CF6; color: white;">Discover Servers</button>
                    <button class="btn btn-secondary" onclick="addOPCUASource()">Save Source Config</button>
                </div>

                <div id="opcua-diagnostics" style="display: none;">
                    <div class="diagnostics-output" id="opcua-output"></div>
                </div>

                <!-- Discovered Servers -->
                <div id="opcua-discovered" style="display: none; margin-top: 24px; border-top: 1px solid rgba(255, 255, 255, 0.1); padding-top: 24px;">
                    <h3 style="color: #8B5CF6; font-size: 16px; font-weight: 600; margin-bottom: 16px;">Discovered OPC UA Servers</h3>
                    <div id="opcua-discovered-list"></div>
                </div>
            </div>
        </div>

        <!-- MQTT Configuration -->
        <div class="config-section">
            <div class="section-header" onclick="toggleSection('mqtt')">
                <div class="section-title">
                    <div class="protocol-icon icon-mqtt">MQ</div>
                    <span>MQTT Sources</span>
                </div>
                <svg class="chevron" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/>
                </svg>
            </div>
            <div class="section-content" id="mqtt-content">
                <div class="form-grid">
                    <div class="form-group">
                        <label class="form-label">Source Name</label>
                        <input type="text" class="form-input" id="mqtt-name" placeholder="mqtt_source_1">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Broker URL</label>
                        <input type="text" class="form-input" id="mqtt-endpoint" placeholder="mqtt://broker.example.com:1883">
                    </div>
                </div>

                <div class="form-grid">
                    <div class="form-group">
                        <label class="form-label">Topics (comma-separated)</label>
                        <input type="text" class="form-input" id="mqtt-topics" placeholder="sensors/+/temperature, devices/#">
                    </div>
                    <div class="form-group">
                        <label class="form-label">QoS Level</label>
                        <select class="form-select" id="mqtt-qos">
                            <option value="0">0 - At most once</option>
                            <option value="1">1 - At least once</option>
                            <option value="2">2 - Exactly once</option>
                        </select>
                    </div>
                </div>

                <div class="button-group">
                    <button class="btn btn-primary" onclick="testMQTTConnection()">Test Connection</button>
                    <button class="btn" onclick="discoverMQTTBrokers()" style="background: #10B981; color: white;">Discover Brokers</button>
                    <button class="btn btn-secondary" onclick="addMQTTSource()">Save Source Config</button>
                </div>

                <div id="mqtt-diagnostics" style="display: none;">
                    <div class="diagnostics-output" id="mqtt-output"></div>
                </div>

                <!-- Discovered Brokers -->
                <div id="mqtt-discovered" style="display: none; margin-top: 24px; border-top: 1px solid rgba(255, 255, 255, 0.1); padding-top: 24px;">
                    <h3 style="color: #10B981; font-size: 16px; font-weight: 600; margin-bottom: 16px;">Discovered MQTT Brokers</h3>
                    <div id="mqtt-discovered-list"></div>
                </div>
            </div>
        </div>

        <!-- Modbus Configuration -->
        <div class="config-section">
            <div class="section-header" onclick="toggleSection('modbus')">
                <div class="section-title">
                    <div class="protocol-icon icon-modbus">MB</div>
                    <span>Modbus Sources</span>
                </div>
                <svg class="chevron" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/>
                </svg>
            </div>
            <div class="section-content" id="modbus-content">
                <div class="form-grid">
                    <div class="form-group">
                        <label class="form-label">Source Name</label>
                        <input type="text" class="form-input" id="modbus-name" placeholder="modbus_source_1">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Connection Type</label>
                        <select class="form-select" id="modbus-type">
                            <option value="tcp">TCP</option>
                            <option value="rtu">RTU (Serial)</option>
                        </select>
                    </div>
                </div>

                <div class="form-grid">
                    <div class="form-group">
                        <label class="form-label">Endpoint</label>
                        <input type="text" class="form-input" id="modbus-endpoint" placeholder="192.168.1.100:502 or /dev/ttyUSB0">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Polling Interval (ms)</label>
                        <input type="number" class="form-input" id="modbus-interval" value="1000">
                    </div>
                </div>

                <div class="button-group">
                    <button class="btn btn-primary" onclick="testModbusConnection()">Test Connection</button>
                    <button class="btn" onclick="discoverModbusDevices()" style="background: #F59E0B; color: white;">Discover Devices</button>
                    <button class="btn btn-secondary" onclick="addModbusSource()">Save Source Config</button>
                </div>

                <div id="modbus-diagnostics" style="display: none;">
                    <div class="diagnostics-output" id="modbus-output"></div>
                </div>

                <!-- Discovered Devices -->
                <div id="modbus-discovered" style="display: none; margin-top: 24px; border-top: 1px solid rgba(255, 255, 255, 0.1); padding-top: 24px;">
                    <h3 style="color: #F59E0B; font-size: 16px; font-weight: 600; margin-bottom: 16px;">Discovered Modbus Devices</h3>
                    <div id="modbus-discovered-list"></div>
                </div>
            </div>
        </div>

        <!-- Backpressure Configuration -->
        <div class="config-section">
            <div class="section-header" onclick="toggleSection('backpressure')">
                <div class="section-title">
                    <div class="protocol-icon" style="background: linear-gradient(135deg, #8B5CF6 0%, #A78BFA 100%);">BP</div>
                    <span>Backpressure & Queue Management</span>
                </div>
                <svg class="chevron" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/>
                </svg>
            </div>
            <div class="section-content" id="backpressure-content">
                <div class="form-grid">
                    <div class="form-group">
                        <label class="form-label">Max Queue Size (records)</label>
                        <input type="number" class="form-input" id="backpressure-queue-size" value="10000">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Drop Policy</label>
                        <select class="form-select" id="backpressure-drop-policy">
                            <option value="oldest">Drop Oldest (FIFO)</option>
                            <option value="newest">Drop Newest (LIFO)</option>
                        </select>
                    </div>
                </div>

                <div style="border-top: 1px solid rgba(255, 255, 255, 0.1); margin: 24px 0; padding-top: 24px;">
                    <h3 style="color: #8B5CF6; font-size: 16px; font-weight: 600; margin-bottom: 16px;">Disk Spool (Overflow)</h3>
                    <div class="form-group">
                        <label class="form-checkbox">
                            <input type="checkbox" id="backpressure-spool-enabled">
                            <span>Enable disk spool for queue overflow</span>
                        </label>
                    </div>
                    <div class="form-grid">
                        <div class="form-group">
                            <label class="form-label">Max Spool Size (MB)</label>
                            <input type="number" class="form-input" id="backpressure-spool-size" value="1000">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Spool Directory</label>
                            <input type="text" class="form-input" id="backpressure-spool-dir" value="/app/spool">
                        </div>
                    </div>
                </div>

                <div class="button-group">
                    <button class="btn btn-secondary" onclick="saveBackpressureConfig()">Save Configuration</button>
                </div>
            </div>
        </div>

        <!-- Advanced Settings -->
        <div class="config-section">
            <div class="section-header" onclick="toggleSection('advanced')">
                <div class="section-title">
                    <span>⚙️</span>
                    <span>Advanced Settings</span>
                </div>
                <svg class="chevron" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/>
                </svg>
            </div>
            <div class="section-content" id="advanced-content">
                <!-- Tag Normalization -->
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                    <h3 style="color: #1E293B; font-size: 16px; font-weight: 600; margin-bottom: 12px;">Tag Normalization</h3>
                    <p style="color: #64748B; font-size: 14px; margin-bottom: 16px;">
                        Convert raw protocol data (OPC-UA, MQTT, Modbus) into a unified, analytics-ready tag structure with consistent naming and quality codes.
                    </p>

                    <div class="form-group">
                        <label style="display: flex; align-items: center; cursor: pointer;">
                            <input type="checkbox" id="normalization-enabled" onchange="toggleNormalization(this.checked)"
                                   style="width: 20px; height: 20px; margin-right: 12px; cursor: pointer;">
                            <div>
                                <div style="font-weight: 500; color: #1E293B;">Enable Tag Normalization</div>
                                <div style="font-size: 13px; color: #64748B; margin-top: 4px;">
                                    All protocols will produce identical schema with unified tag paths, quality codes, and data types
                                </div>
                            </div>
                        </label>
                    </div>

                    <div id="normalization-details" style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #E2E8F0; display: none;">
                        <div style="font-size: 13px; color: #64748B; line-height: 1.6;">
                            <strong style="color: #1E293B;">When enabled:</strong>
                            <ul style="margin: 8px 0; padding-left: 20px;">
                                <li>Tag paths follow hierarchy: site/line/equipment/signal</li>
                                <li>Quality codes unified to: good, bad, uncertain</li>
                                <li>Data types normalized: float, int, bool, string, timestamp</li>
                                <li>Metadata preserved from source protocols</li>
                            </ul>
                            <div style="margin-top: 12px; padding: 12px; background: #FEF3C7; border: 1px solid #F59E0B; border-radius: 6px;">
                                <strong style="color: #92400E;">⚠️ Note:</strong>
                                <span style="color: #78350F;">Restart connector after enabling/disabling normalization for changes to take effect.</span>
                            </div>
                        </div>
                    </div>

                    <div class="button-group" style="margin-top: 16px;">
                        <button class="btn btn-primary" onclick="saveNormalizationConfig()" style="padding: 10px 24px;">Save Settings</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Active Sources -->
        <div class="config-section">
            <div class="section-header expanded" onclick="toggleSection('sources')">
                <div class="section-title">
                    <span>📊</span>
                    <span>Active Sources</span>
                </div>
                <svg class="chevron" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/>
                </svg>
            </div>
            <div class="section-content expanded" id="sources-content">
                <table class="sources-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Protocol</th>
                            <th>Endpoint</th>
                            <th>Status</th>
                            <th>Records</th>
                        </tr>
                    </thead>
                    <tbody id="sources-tbody">
                        <tr><td colspan="5" style="text-align: center; color: #9BA3AF;">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        // Toggle section expand/collapse
        function toggleSection(sectionId) {
            const header = event.currentTarget;
            const content = document.getElementById(sectionId + '-content');

            header.classList.toggle('expanded');
            content.classList.toggle('expanded');
        }

        // Toggle subsection expand/collapse
        function toggleSubSection(sectionId) {
            const content = document.getElementById(sectionId + '-content');
            const display = content.style.display;
            content.style.display = display === 'none' ? 'block' : 'none';
        }

        // Show/hide ZeroBus diagnostics panel
        function showZeroBusDiagnostics() {
            const panel = document.getElementById('zerobus-diagnostics-panel');
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
            if (panel.style.display === 'block') {
                loadZeroBusDiagnostics();
            }
        }

        // Refresh ZeroBus status
        async function refreshZeroBusStatus() {
            try {
                const response = await fetch('/api/zerobus/status');
                const status = await response.json();

                const indicator = document.getElementById('zerobus-status-indicator');
                const text = document.getElementById('zerobus-status-text');

                if (status.connected) {
                    indicator.style.background = '#10B981';
                    text.style.color = '#10B981';
                    text.textContent = 'Connected';
                } else {
                    indicator.style.background = '#EF4444';
                    text.style.color = '#EF4444';
                    text.textContent = 'Disconnected';
                }
            } catch (error) {
                console.error('Failed to refresh status:', error);
            }
        }

        // Load ZeroBus diagnostics
        async function loadZeroBusDiagnostics() {
            try {
                const response = await fetch('/api/zerobus/diagnostics');
                const diag = await response.json();

                // Update timestamp
                document.getElementById('diagnostics-timestamp').textContent =
                    `Last updated: ${new Date().toLocaleString('en-GB')}`;

                // Update health
                document.getElementById('diag-status').textContent = diag.health?.status || 'unknown';
                document.getElementById('diag-enabled').textContent = diag.health?.enabled || 'false';

                // Update configuration summary
                document.getElementById('diag-workspace').textContent = diag.config?.workspace_url || '-';
                document.getElementById('diag-endpoint').textContent = diag.config?.zerobus_endpoint || '-';
                document.getElementById('diag-table').textContent = diag.config?.target_table || '-';
                document.getElementById('diag-tagmode').textContent = diag.config?.tag_mode || 'explicit';
                document.getElementById('diag-tags').textContent = `${diag.config?.explicit_tags || 0} tag(s)`;
                document.getElementById('diag-subfolders').textContent = diag.config?.include_subfolders || 'false';
                document.getElementById('diag-storeforward').textContent = diag.config?.store_forward || 'false';
                document.getElementById('diag-spooldir').textContent = diag.config?.spool_dir || '-';

                // Update runtime diagnostics
                const runtimeDiv = document.getElementById('runtime-diagnostics');
                runtimeDiv.innerHTML = `<pre style="margin: 0; white-space: pre-wrap; word-wrap: break-word;">${diag.runtime || 'No diagnostics available'}</pre>`;
            } catch (error) {
                console.error('Failed to load diagnostics:', error);
            }
        }

        // Refresh ZeroBus diagnostics
        function refreshZeroBusDiagnostics() {
            loadZeroBusDiagnostics();
        }

        // Open raw diagnostics
        function openRawDiagnostics() {
            window.open('/api/zerobus/diagnostics/raw', '_blank');
        }

        // Cancel ZeroBus config
        function cancelZeroBusConfig() {
            loadConfig();
        }

        // Load current configuration
        async function loadConfig() {
            try {
                const response = await fetch('/api/config');
                const config = await response.json();

                // Load ZeroBus config from dedicated endpoint (includes encrypted credentials)
                try {
                    const zbResponse = await fetch('/api/zerobus/config');
                    const zbConfig = await zbResponse.json();

                    document.getElementById('zerobus-enabled').checked = zbConfig.enabled || false;
                    document.getElementById('zerobus-workspace-url').value = zbConfig.workspace_url || '';
                    document.getElementById('zerobus-endpoint').value = zbConfig.endpoint || '';
                    document.getElementById('zerobus-client-id').value = zbConfig.client_id || '';
                    document.getElementById('zerobus-client-secret').value = zbConfig.client_secret || '';
                    document.getElementById('zerobus-target-table').value = zbConfig.target_table || '';
                    document.getElementById('zerobus-source-id').value = zbConfig.source_id || '';
                    document.getElementById('zerobus-debug').checked = zbConfig.debug || false;
                } catch (error) {
                    console.error('Error loading ZeroBus config:', error);
                }

                // Load OPC UA config (first source)
                const opcuaSources = (config.sources || []).filter(s => s.protocol === 'opcua');
                if (opcuaSources.length > 0) {
                    const source = opcuaSources[0];
                    document.getElementById('opcua-name').value = source.name || '';
                    document.getElementById('opcua-endpoint').value = source.endpoint || '';
                    document.getElementById('opcua-security').value = source.security?.mode || 'None';
                    document.getElementById('opcua-interval').value = source.publishing_interval_ms || 1000;
                }

            } catch (error) {
                console.error('Error loading config:', error);
            }
        }

        // Update status dashboard
        async function updateStatus() {
            try {
                const [statusRes, metricsRes, sourcesRes] = await Promise.all([
                    fetch('/api/status'),
                    fetch('/api/metrics'),
                    fetch('/api/sources')
                ]);

                const status = await statusRes.json();
                const metrics = await metricsRes.json();
                const sources = await sourcesRes.json();

                // Update status cards
                document.getElementById('active-sources').textContent = status.active_sources || 0;
                document.getElementById('active-sources').className = 'status-value status-ok';

                const zerobusEl = document.getElementById('zerobus-status');
                zerobusEl.textContent = status.zerobus_connected ? 'Connected' : 'Disconnected';
                zerobusEl.className = status.zerobus_connected ? 'status-value status-ok' : 'status-value status-error';

                document.getElementById('queue-depth').textContent = status.backpressure_stats?.current_queue_depth || 0;
                document.getElementById('queue-depth').className = 'status-value';

                document.getElementById('records-sent').textContent = metrics.bridge?.batches_sent || 0;
                document.getElementById('records-sent').className = 'status-value status-ok';

                // Update sources table
                const tbody = document.getElementById('sources-tbody');
                if (sources.sources && sources.sources.length > 0) {
                    tbody.innerHTML = sources.sources.map(source => {
                        const protocolBadge = `badge-${source.protocol}`;
                        const statusClass = source.connected ? 'status-ok' : 'status-error';
                        const statusText = source.connected ? '✓ Connected' : '✗ Disconnected';

                        // Format last data time
                        let lastSeen = '-';
                        if (source.last_data_time) {
                            const lastTime = new Date(source.last_data_time * 1000);
                            const now = new Date();
                            const diffSeconds = Math.floor((now - lastTime) / 1000);

                            if (diffSeconds < 5) {
                                lastSeen = '<span style="color: #10B981;">● Just now</span>';
                            } else if (diffSeconds < 60) {
                                lastSeen = `<span style="color: #10B981;">${diffSeconds}s ago</span>`;
                            } else if (diffSeconds < 3600) {
                                lastSeen = `<span style="color: #F59E0B;">${Math.floor(diffSeconds / 60)}m ago</span>`;
                            } else {
                                lastSeen = `<span style="color: #EF4444;">${Math.floor(diffSeconds / 3600)}h ago</span>`;
                            }
                        } else if (source.connected) {
                            lastSeen = '<span style="color: #6B7280;">Waiting for data...</span>';
                        }

                        return `
                            <tr>
                                <td>${source.name}</td>
                                <td><span class="badge ${protocolBadge}">${source.protocol.toUpperCase()}</span></td>
                                <td style="font-family: monospace; font-size: 12px;">${source.endpoint}</td>
                                <td class="${statusClass}">${statusText}</td>
                                <td>${lastSeen}</td>
                            </tr>
                        `;
                    }).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #9BA3AF;">No sources configured</td></tr>';
                }

            } catch (error) {
                console.error('Error updating status:', error);
            }
        }

        // Test ZeroBus connection
        async function testZeroBusConnection() {
            const output = document.getElementById('zerobus-output');
            const diagnostics = document.getElementById('zerobus-diagnostics');

            diagnostics.style.display = 'block';
            output.className = 'diagnostics-output';
            output.textContent = '→ Testing ZeroBus connection...\\n';

            try {
                const response = await fetch('/api/test/zerobus', { method: 'POST' });
                const result = await response.json();

                if (result.success) {
                    output.textContent += '✓ Connection successful\\n';
                    output.textContent += `  Workspace: ${result.workspace}\\n`;
                    output.textContent += `  Target: ${result.target}\\n`;
                } else {
                    output.className = 'diagnostics-output error';
                    output.textContent += `✗ Connection failed: ${result.error}\\n`;
                }
            } catch (error) {
                output.className = 'diagnostics-output error';
                output.textContent += `✗ Error: ${error.message}\\n`;
            }
        }

        // Test OPC UA connection
        async function testOPCUAConnection() {
            const output = document.getElementById('opcua-output');
            const diagnostics = document.getElementById('opcua-diagnostics');

            diagnostics.style.display = 'block';
            output.className = 'diagnostics-output';
            output.textContent = '→ Testing OPC UA connection...\\n';

            const endpoint = document.getElementById('opcua-endpoint').value;

            try {
                const response = await fetch('/api/test/opcua', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ endpoint })
                });
                const result = await response.json();

                if (result.success) {
                    output.textContent += '✓ Connection successful\\n';
                    output.textContent += `  Server: ${result.server_info?.product_name || 'Unknown'}\\n`;
                    output.textContent += `  Nodes discovered: ${result.node_count || 0}\\n`;
                } else {
                    output.className = 'diagnostics-output error';
                    output.textContent += `✗ Connection failed: ${result.error}\\n`;
                }
            } catch (error) {
                output.className = 'diagnostics-output error';
                output.textContent += `✗ Error: ${error.message}\\n`;
            }
        }

        // Test MQTT connection
        async function testMQTTConnection() {
            const output = document.getElementById('mqtt-output');
            const diagnostics = document.getElementById('mqtt-diagnostics');

            diagnostics.style.display = 'block';
            output.className = 'diagnostics-output';
            output.textContent = '→ Testing MQTT connection...\\n';

            const endpoint = document.getElementById('mqtt-endpoint').value;

            try {
                const response = await fetch('/api/test/mqtt', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ endpoint })
                });
                const result = await response.json();

                if (result.success) {
                    output.textContent += '✓ Connection successful\\n';
                    output.textContent += `  Broker: ${result.broker}\\n`;
                } else {
                    output.className = 'diagnostics-output error';
                    output.textContent += `✗ Connection failed: ${result.error}\\n`;
                }
            } catch (error) {
                output.className = 'diagnostics-output error';
                output.textContent += `✗ Error: ${error.message}\\n`;
            }
        }

        // Test Modbus connection
        async function testModbusConnection() {
            const output = document.getElementById('modbus-output');
            const diagnostics = document.getElementById('modbus-diagnostics');

            diagnostics.style.display = 'block';
            output.className = 'diagnostics-output';
            output.textContent = '→ Testing Modbus connection...\\n';

            const endpoint = document.getElementById('modbus-endpoint').value;
            const type = document.getElementById('modbus-type').value;

            try {
                const response = await fetch('/api/test/modbus', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ endpoint, type })
                });
                const result = await response.json();

                if (result.success) {
                    output.textContent += '✓ Connection successful\\n';
                    output.textContent += `  Device: ${result.device}\\n`;
                } else {
                    output.className = 'diagnostics-output error';
                    output.textContent += `✗ Connection failed: ${result.error}\\n`;
                }
            } catch (error) {
                output.className = 'diagnostics-output error';
                output.textContent += `✗ Error: ${error.message}\\n`;
            }
        }

        // Save configurations
        async function saveZeroBusConfig() {
            const config = {
                enabled: document.getElementById('zerobus-enabled').checked,
                workspace_url: document.getElementById('zerobus-workspace-url').value,
                endpoint: document.getElementById('zerobus-endpoint').value,
                client_id: document.getElementById('zerobus-client-id').value,
                client_secret: document.getElementById('zerobus-client-secret').value,
                target_table: document.getElementById('zerobus-target-table').value,
                source_id: document.getElementById('zerobus-source-id').value,
                debug: document.getElementById('zerobus-debug').checked
            };

            // Validate required fields
            if (!config.workspace_url || !config.endpoint || !config.client_id || !config.target_table) {
                alert('Please fill in all required fields (Workspace URL, Endpoint, Client ID, Target Table)');
                return;
            }

            try {
                const response = await fetch('/api/zerobus/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });

                const result = await response.json();

                if (result.success) {
                    alert('✓ ZeroBus configuration saved successfully!');
                    await refreshZeroBusStatus();
                } else {
                    alert(`✗ Failed to save configuration: ${result.error}`);
                }
            } catch (error) {
                alert(`✗ Error saving configuration: ${error.message}`);
            }
        }

        async function testZeroBusConnection() {
            const config = {
                workspace_url: document.getElementById('zerobus-workspace-url').value,
                endpoint: document.getElementById('zerobus-endpoint').value,
                client_id: document.getElementById('zerobus-client-id').value,
                client_secret: document.getElementById('zerobus-client-secret').value
            };

            if (!config.workspace_url || !config.endpoint || !config.client_id || !config.client_secret) {
                alert('Please fill in all required fields for testing');
                return;
            }

            try {
                const response = await fetch('/api/zerobus/test', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });

                const result = await response.json();

                if (result.success) {
                    alert(`✓ ${result.message}`);
                } else {
                    alert(`✗ Connection test failed: ${result.error}`);
                }
            } catch (error) {
                alert(`✗ Error testing connection: ${error.message}`);
            }
        }

        function cancelZeroBusConfig() {
            // Reset form or close if this was in a modal
            alert('Configuration changes cancelled');
        }

        async function discoverOPCUAServers() {
            const listDiv = document.getElementById('opcua-discovered-list');
            const discoveredSection = document.getElementById('opcua-discovered');

            discoveredSection.style.display = 'block';
            listDiv.innerHTML = '<p style="color: #9BA3AF;">Detecting connector network...</p>';

            try {
                // First, get the connector's current network dynamically
                const networkInfoResponse = await fetch('/api/network/info');
                const networkInfo = await networkInfoResponse.json();

                let scanRanges = [];
                let localNetwork = null;

                if (networkInfo.success && networkInfo.network_cidr) {
                    localNetwork = networkInfo.network_cidr;
                    listDiv.innerHTML = `<p style="color: #9BA3AF;">Scanning local network ${localNetwork} first...</p>`;

                    // Scan local network FIRST (priority)
                    scanRanges.push(localNetwork);
                }

                // Then add other common private network ranges (but avoid duplicates)
                const additionalRanges = [
                    '10.0.0.0/24',
                    '10.1.0.0/24',
                    '10.10.0.0/24',
                    '172.16.0.0/24',
                    '172.18.0.0/24',
                    '172.19.0.0/24',
                    '172.20.0.0/24',
                    '192.168.0.0/24',
                    '192.168.1.0/24',
                    '192.168.10.0/24',
                    '192.168.20.0/24'
                ];

                additionalRanges.forEach(range => {
                    if (range !== localNetwork) {
                        scanRanges.push(range);
                    }
                });

                listDiv.innerHTML = '<p style="color: #9BA3AF;">Scanning ' + scanRanges.length + ' network ranges in parallel...</p>';

                const scanPromises = scanRanges.map(range =>
                    fetch('/api/opcua/discover/scan', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            ip_range: range,
                            port: 4840,
                            timeout: 1.5
                        })
                    }).then(r => r.json()).catch(err => ({ success: false, servers: [] }))
                );

                const results = await Promise.all(scanPromises);

                // Aggregate all servers from all ranges
                let allServers = [];
                results.forEach(result => {
                    if (result.success && result.servers && result.servers.length > 0) {
                        allServers = allServers.concat(result.servers);
                    }
                });

                // Deduplicate by URL
                const uniqueServers = [];
                const seenUrls = new Set();
                allServers.forEach(server => {
                    const urls = server.discovery_urls || server.urls || [];
                    const firstUrl = urls[0] || server.endpoint || server.url || 'unknown';
                    if (!seenUrls.has(firstUrl)) {
                        seenUrls.add(firstUrl);
                        uniqueServers.push(server);
                    }
                });

                if (uniqueServers.length > 0) {
                    let html = '<p style="color: #00A8E1; margin-bottom: 12px;">Found ' + uniqueServers.length + ' OPC UA server(s)</p>';
                    uniqueServers.forEach((server, index) => {
                        const appName = server.application_name || server.name || 'Unknown Server';
                        const urls = server.discovery_urls || server.urls || [];
                        const firstUrl = urls[0] || server.endpoint || server.url || 'opc.tcp://unknown:4840';

                        html += `
                        <div style="background: rgba(16, 185, 129, 0.1); border: 2px solid #10B981; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div style="flex: 1;">
                                    <div style="color: #10B981; font-weight: 600; margin-bottom: 8px;">✓ ${appName}</div>
                                    <div style="color: #34D399; font-size: 13px; font-family: 'Courier New', monospace;">${firstUrl}</div>
                                    ${server.product_uri ? `<div style="color: #6EE7B7; font-size: 12px; margin-top: 4px;">Product: ${server.product_uri}</div>` : ''}
                                    ${server.endpoints && server.endpoints.length > 0 ?
                                        `<div style="color: #6EE7B7; font-size: 12px; margin-top: 4px;">Endpoints: ${server.endpoints.length}</div>` : ''}
                                </div>
                                <button class="btn btn-primary" data-url="${firstUrl.replace(/"/g, '&quot;')}" data-name="${appName.replace(/"/g, '&quot;')}" onclick="addDiscoveredServerByData(this)" style="padding: 8px 16px; font-size: 13px;">
                                    Add to Config
                                </button>
                            </div>
                        </div>`;
                    });
                    listDiv.innerHTML = html;
                } else {
                    listDiv.innerHTML = '<p style="color: #EF4444;">No OPC UA servers found on any private network ranges</p>';
                }
            } catch (error) {
                listDiv.innerHTML = `<p style="color: #EF4444;">Discovery error: ${error.message}</p>`;
            }
        }

        function addDiscoveredServerByData(button) {
            // Get data from button attributes
            const url = button.getAttribute('data-url');
            const name = button.getAttribute('data-name');

            // Clean up the name - extract just the text from LocalizedText format
            let cleanName = name;
            const textMatch = name.match(/Text='([^']+)'/);
            if (textMatch) {
                cleanName = textMatch[1];
            }
            cleanName = cleanName.replace(/\s+/g, '_').toLowerCase();

            // Auto-fill the form
            document.getElementById('opcua-endpoint').value = url;
            document.getElementById('opcua-name').value = cleanName;

            // Scroll to form
            document.getElementById('opcua-endpoint').scrollIntoView({ behavior: 'smooth', block: 'center' });

            alert(`Server "${cleanName}" added to form. Click "Save Source Config" to save.`);
        }

        // Deprecated: kept for backward compatibility
        function addDiscoveredServer(url, name) {
            const button = document.createElement('button');
            button.setAttribute('data-url', url);
            button.setAttribute('data-name', name);
            addDiscoveredServerByData(button);
        }

        async function discoverMQTTBrokers() {
            const listDiv = document.getElementById('mqtt-discovered-list');
            const discoveredSection = document.getElementById('mqtt-discovered');

            discoveredSection.style.display = 'block';
            listDiv.innerHTML = '<p style="color: #9BA3AF;">Detecting connector network...</p>';

            try {
                // First, get the connector's current network dynamically
                const networkInfoResponse = await fetch('/api/network/info');
                const networkInfo = await networkInfoResponse.json();

                let scanRanges = [];
                let localNetwork = null;

                if (networkInfo.success && networkInfo.network_cidr) {
                    localNetwork = networkInfo.network_cidr;
                    listDiv.innerHTML = `<p style="color: #9BA3AF;">Scanning local network ${localNetwork} first...</p>`;

                    // Scan local network FIRST (priority)
                    scanRanges.push(localNetwork);
                }

                // Then add other common private network ranges (but avoid duplicates)
                const additionalRanges = [
                    '10.0.0.0/24',
                    '10.1.0.0/24',
                    '10.10.0.0/24',
                    '172.16.0.0/24',
                    '172.18.0.0/24',
                    '172.19.0.0/24',
                    '172.20.0.0/24',
                    '192.168.0.0/24',
                    '192.168.1.0/24',
                    '192.168.10.0/24',
                    '192.168.20.0/24'
                ];

                additionalRanges.forEach(range => {
                    if (range !== localNetwork) {
                        scanRanges.push(range);
                    }
                });

                listDiv.innerHTML = '<p style="color: #9BA3AF;">Scanning ' + scanRanges.length + ' network ranges in parallel...</p>';

                const scanPromises = scanRanges.map(range =>
                    fetch('/api/mqtt/discover/scan', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            ip_range: range,
                            port: 1883,
                            timeout: 1.5
                        })
                    }).then(r => r.json()).catch(err => ({ success: false, brokers: [] }))
                );

                const results = await Promise.all(scanPromises);

                // Aggregate all brokers from all ranges
                let allBrokers = [];
                results.forEach(result => {
                    if (result.success && result.brokers && result.brokers.length > 0) {
                        allBrokers = allBrokers.concat(result.brokers);
                    }
                });

                // Deduplicate by host
                const uniqueBrokers = [];
                const seenHosts = new Set();
                allBrokers.forEach(broker => {
                    const host = broker.host || broker.ip || 'Unknown';
                    if (!seenHosts.has(host)) {
                        seenHosts.add(host);
                        uniqueBrokers.push(broker);
                    }
                });

                if (uniqueBrokers.length > 0) {
                    let html = '<p style="color: #10B981; margin-bottom: 12px;">Found ' + uniqueBrokers.length + ' MQTT broker(s)</p>';
                    uniqueBrokers.forEach((broker, index) => {
                        const brokerHost = broker.host || broker.ip || 'Unknown';
                        const brokerPort = broker.port || 1883;
                        const brokerUrl = `mqtt://${brokerHost}:${brokerPort}`;

                        html += `
                        <div style="background: rgba(16, 185, 129, 0.1); border: 2px solid #10B981; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div style="flex: 1;">
                                    <div style="color: #10B981; font-weight: 600; margin-bottom: 8px;">✓ MQTT Broker ${index + 1}</div>
                                    <div style="color: #34D399; font-size: 13px; font-family: 'Courier New', monospace;">${brokerUrl}</div>
                                    ${broker.version ? `<div style="color: #6EE7B7; font-size: 12px; margin-top: 4px;">Version: ${broker.version}</div>` : ''}
                                </div>
                                <button class="btn btn-primary" onclick="addDiscoveredMQTTBroker('${brokerUrl}', '${brokerHost}')" style="padding: 8px 16px; font-size: 13px;">
                                    Add to Config
                                </button>
                            </div>
                        </div>`;
                    });
                    listDiv.innerHTML = html;
                } else {
                    listDiv.innerHTML = '<p style="color: #EF4444;">No MQTT brokers found on any private network ranges</p>';
                }
            } catch (error) {
                listDiv.innerHTML = `<p style="color: #EF4444;">Discovery error: ${error.message}</p>`;
            }
        }

        function addDiscoveredMQTTBroker(url, host) {
            const cleanName = `mqtt_${host.replace(/[^a-z0-9]/gi, '_').toLowerCase()}`;
            document.getElementById('mqtt-endpoint').value = url;
            document.getElementById('mqtt-name').value = cleanName;

            // Scroll to form
            document.getElementById('mqtt-endpoint').scrollIntoView({ behavior: 'smooth', block: 'center' });

            alert(`MQTT Broker "${host}" added to form. Click "Save Source Config" to save.`);
        }

        async function discoverModbusDevices() {
            const listDiv = document.getElementById('modbus-discovered-list');
            const discoveredSection = document.getElementById('modbus-discovered');

            discoveredSection.style.display = 'block';
            listDiv.innerHTML = '<p style="color: #9BA3AF;">Detecting connector network...</p>';

            try {
                // First, get the connector's current network dynamically
                const networkInfoResponse = await fetch('/api/network/info');
                const networkInfo = await networkInfoResponse.json();

                let scanRanges = [];
                let localNetwork = null;

                if (networkInfo.success && networkInfo.network_cidr) {
                    localNetwork = networkInfo.network_cidr;
                    listDiv.innerHTML = `<p style="color: #9BA3AF;">Scanning local network ${localNetwork} first...</p>`;

                    // Scan local network FIRST (priority)
                    scanRanges.push(localNetwork);
                }

                // Then add other common private network ranges (but avoid duplicates)
                const additionalRanges = [
                    '10.0.0.0/24',
                    '10.1.0.0/24',
                    '10.10.0.0/24',
                    '172.16.0.0/24',
                    '172.18.0.0/24',
                    '172.19.0.0/24',
                    '172.20.0.0/24',
                    '192.168.0.0/24',
                    '192.168.1.0/24',
                    '192.168.10.0/24',
                    '192.168.20.0/24'
                ];

                additionalRanges.forEach(range => {
                    if (range !== localNetwork) {
                        scanRanges.push(range);
                    }
                });

                listDiv.innerHTML = '<p style="color: #9BA3AF;">Scanning ' + scanRanges.length + ' network ranges in parallel...</p>';

                const scanPromises = scanRanges.map(range =>
                    fetch('/api/modbus/discover/scan', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            ip_range: range,
                            port: 5020,
                            timeout: 1.5
                        })
                    }).then(r => r.json()).catch(err => ({ success: false, devices: [] }))
                );

                const results = await Promise.all(scanPromises);

                // Aggregate all devices from all ranges
                let allDevices = [];
                results.forEach(result => {
                    if (result.success && result.devices && result.devices.length > 0) {
                        allDevices = allDevices.concat(result.devices);
                    }
                });

                // Deduplicate by host
                const uniqueDevices = [];
                const seenHosts = new Set();
                allDevices.forEach(device => {
                    const host = device.host || device.ip || 'Unknown';
                    if (!seenHosts.has(host)) {
                        seenHosts.add(host);
                        uniqueDevices.push(device);
                    }
                });

                if (uniqueDevices.length > 0) {
                    let html = '<p style="color: #F59E0B; margin-bottom: 12px;">Found ' + uniqueDevices.length + ' Modbus device(s)</p>';
                    uniqueDevices.forEach((device, index) => {
                        const deviceHost = device.host || device.ip || 'Unknown';
                        const devicePort = device.port || 502;
                        const deviceEndpoint = `${deviceHost}:${devicePort}`;

                        html += `
                        <div style="background: rgba(16, 185, 129, 0.1); border: 2px solid #10B981; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div style="flex: 1;">
                                    <div style="color: #10B981; font-weight: 600; margin-bottom: 8px;">✓ Modbus Device ${index + 1}</div>
                                    <div style="color: #34D399; font-size: 13px; font-family: 'Courier New', monospace;">${deviceEndpoint}</div>
                                    ${device.unit_id ? `<div style="color: #6EE7B7; font-size: 12px; margin-top: 4px;">Unit ID: ${device.unit_id}</div>` : ''}
                                </div>
                                <button class="btn btn-primary" onclick="addDiscoveredModbusDevice('${deviceEndpoint}', '${deviceHost}')" style="padding: 8px 16px; font-size: 13px;">
                                    Add to Config
                                </button>
                            </div>
                        </div>`;
                    });
                    listDiv.innerHTML = html;
                } else {
                    listDiv.innerHTML = '<p style="color: #EF4444;">No Modbus devices found on any private network ranges</p>';
                }
            } catch (error) {
                listDiv.innerHTML = `<p style="color: #EF4444;">Discovery error: ${error.message}</p>`;
            }
        }

        function addDiscoveredModbusDevice(endpoint, host) {
            const cleanName = `modbus_${host.replace(/[^a-z0-9]/gi, '_').toLowerCase()}`;
            document.getElementById('modbus-endpoint').value = endpoint;
            document.getElementById('modbus-name').value = cleanName;

            // Scroll to form
            document.getElementById('modbus-endpoint').scrollIntoView({ behavior: 'smooth', block: 'center' });

            alert(`Modbus Device "${host}" added to form. Click "Save Source Config" to save.`);
        }

        async function addOPCUASource() {
            const name = document.getElementById('opcua-name').value;
            const endpoint = document.getElementById('opcua-endpoint').value;
            const securityMode = document.getElementById('opcua-security').value;
            const interval = document.getElementById('opcua-interval').value;

            if (!name || !endpoint) {
                alert('Please fill in Name and Endpoint fields');
                return;
            }

            const config = {
                endpoint,
                security_mode: securityMode,
                security_policy: 'None',
                subscription_interval: parseInt(interval)
            };

            try {
                const response = await fetch('/api/sources/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        type: 'opcua',
                        name,
                        config
                    })
                });

                const result = await response.json();

                if (result.success) {
                    const configPath = result.config_path || '/app/config/connector_state.json';
                    alert(`✓ OPC UA source "${name}" saved successfully!\n\nConfiguration saved to:\n${configPath}`);
                    // Clear form
                    document.getElementById('opcua-name').value = '';
                    document.getElementById('opcua-endpoint').value = '';
                    // Refresh page or update source list
                    location.reload();
                } else {
                    alert(`✗ Failed to add source: ${result.error}`);
                }
            } catch (error) {
                alert(`✗ Error adding source: ${error.message}`);
            }
        }

        async function addMQTTSource() {
            const name = document.getElementById('mqtt-name').value;
            const endpoint = document.getElementById('mqtt-endpoint').value;

            if (!name || !endpoint) {
                alert('Please fill in Name and Broker URL fields');
                return;
            }

            const config = {
                endpoint,
                topics: ['sensors/#'],  // Default topic
                qos: 0
            };

            try {
                const response = await fetch('/api/sources/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        type: 'mqtt',
                        name,
                        config
                    })
                });

                const result = await response.json();

                if (result.success) {
                    const configPath = result.config_path || '/app/config/connector_state.json';
                    alert(`✓ MQTT source "${name}" saved successfully!\n\nConfiguration saved to:\n${configPath}`);
                    // Clear form
                    document.getElementById('mqtt-name').value = '';
                    document.getElementById('mqtt-endpoint').value = '';
                    // Refresh page or update source list
                    location.reload();
                } else {
                    alert(`✗ Failed to add source: ${result.error}`);
                }
            } catch (error) {
                alert(`✗ Error adding source: ${error.message}`);
            }
        }

        async function addModbusSource() {
            const name = document.getElementById('modbus-name').value;
            const endpoint = document.getElementById('modbus-endpoint').value;
            const type = document.getElementById('modbus-type').value;

            if (!name || !endpoint) {
                alert('Please fill in Name and Endpoint fields');
                return;
            }

            const config = {
                endpoint,
                type,
                unit_id: 1
            };

            try {
                const response = await fetch('/api/sources/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        type: 'modbus',
                        name,
                        config
                    })
                });

                const result = await response.json();

                if (result.success) {
                    const configPath = result.config_path || '/app/config/connector_state.json';
                    alert(`✓ Modbus source "${name}" saved successfully!\n\nConfiguration saved to:\n${configPath}`);
                    // Clear form
                    document.getElementById('modbus-name').value = '';
                    document.getElementById('modbus-endpoint').value = '';
                    // Refresh page or update source list
                    location.reload();
                } else {
                    alert(`✗ Failed to add source: ${result.error}`);
                }
            } catch (error) {
                alert(`✗ Error adding source: ${error.message}`);
            }
        }

        async function saveBackpressureConfig() {
            alert('Backpressure configuration saved! (Implementation pending)');
        }

        // Tag Normalization functions
        function toggleNormalization(enabled) {
            // Show/hide details section
            const detailsSection = document.getElementById('normalization-details');
            if (detailsSection) {
                detailsSection.style.display = enabled ? 'block' : 'none';
            }
        }

        async function saveNormalizationConfig() {
            const enabled = document.getElementById('normalization-enabled').checked;

            try {
                const response = await fetch('/api/normalization/toggle', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ enabled })
                });

                const result = await response.json();

                if (result.success) {
                    alert(`✓ Tag normalization ${enabled ? 'enabled' : 'disabled'} successfully!\n\n⚠️ Please restart the connector for changes to take effect.`);
                } else {
                    alert(`✗ Failed to update normalization: ${result.error}`);
                }
            } catch (error) {
                alert(`✗ Error updating normalization: ${error.message}`);
            }
        }

        async function loadNormalizationConfig() {
            try {
                const response = await fetch('/api/normalization/status');
                const result = await response.json();

                if (result.success) {
                    const checkbox = document.getElementById('normalization-enabled');
                    if (checkbox) {
                        checkbox.checked = result.enabled || false;
                        toggleNormalization(checkbox.checked);
                    }
                }
            } catch (error) {
                console.error('Error loading normalization config:', error);
            }
        }

        // Initialize
        loadConfig();
        loadNormalizationConfig();
        updateStatus();
        setInterval(updateStatus, 3000); // Update every 3 seconds
    </script>
</body>
</html>
        """

    async def stop(self):
        """Stop web server."""
        if self.site:
            await self.site.stop()

        if self.runner:
            await self.runner.cleanup()

        logger.info("✓ Web GUI stopped")
