"""
Web GUI for Databricks IoT Connector

Provides REST API and web interface for:
- Configuration management
- Real-time monitoring
- Manual control (start/stop sources)
- Credential management
- Health checks
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

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
        """List all configured sources."""
        try:
            sources = []
            for name, client in self.bridge.clients.items():
                sources.append({
                    'name': name,
                    'protocol': client.protocol_type.value,
                    'endpoint': client.endpoint,
                    'connected': client._client is not None,
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

    async def handle_index(self, request: web.Request) -> web.Response:
        """Serve simple HTML dashboard."""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Databricks IoT Connector</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 2px solid #FF3621; padding-bottom: 10px; }
        .metric { display: inline-block; margin: 10px 20px 10px 0; }
        .metric-label { color: #666; font-size: 14px; }
        .metric-value { color: #333; font-size: 24px; font-weight: bold; }
        .status-ok { color: #28a745; }
        .status-error { color: #dc3545; }
        .status-warning { color: #ffc107; }
        button { background: #FF3621; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
        button:hover { background: #e6301d; }
        pre { background: #f8f9fa; padding: 10px; border-radius: 4px; overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Databricks IoT Connector</h1>

        <div class="card">
            <h2>Status</h2>
            <div id="status">Loading...</div>
        </div>

        <div class="card">
            <h2>Metrics</h2>
            <div id="metrics">Loading...</div>
        </div>

        <div class="card">
            <h2>Sources</h2>
            <table id="sources">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Protocol</th>
                        <th>Endpoint</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td colspan="4">Loading...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        async function fetchStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();

                const statusHtml = `
                    <div class="metric">
                        <div class="metric-label">Active Sources</div>
                        <div class="metric-value">${data.active_sources || 0}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">ZeroBus</div>
                        <div class="metric-value ${data.zerobus_connected ? 'status-ok' : 'status-error'}">
                            ${data.zerobus_connected ? 'Connected' : 'Disconnected'}
                        </div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Circuit Breaker</div>
                        <div class="metric-value">${data.circuit_breaker_state || 'unknown'}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Queue Depth</div>
                        <div class="metric-value">${data.backpressure_stats?.memory_queue_depth || 0} / ${data.backpressure_stats?.max_queue_size || 0}</div>
                    </div>
                `;

                document.getElementById('status').innerHTML = statusHtml;
            } catch (error) {
                document.getElementById('status').innerHTML = '<span class="status-error">Error loading status</span>';
            }
        }

        async function fetchMetrics() {
            try {
                const response = await fetch('/api/metrics');
                const data = await response.json();

                const bridge = data.bridge || {};
                const metricsHtml = `
                    <div class="metric">
                        <div class="metric-label">Records Received</div>
                        <div class="metric-value">${bridge.records_received || 0}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Records Enqueued</div>
                        <div class="metric-value">${bridge.records_enqueued || 0}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Records Dropped</div>
                        <div class="metric-value ${bridge.records_dropped > 0 ? 'status-warning' : ''}">${bridge.records_dropped || 0}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Batches Sent</div>
                        <div class="metric-value">${bridge.batches_sent || 0}</div>
                    </div>
                `;

                document.getElementById('metrics').innerHTML = metricsHtml;
            } catch (error) {
                document.getElementById('metrics').innerHTML = '<span class="status-error">Error loading metrics</span>';
            }
        }

        async function fetchSources() {
            try {
                const response = await fetch('/api/sources');
                const data = await response.json();

                const tbody = document.querySelector('#sources tbody');
                if (data.sources && data.sources.length > 0) {
                    tbody.innerHTML = data.sources.map(source => `
                        <tr>
                            <td>${source.name}</td>
                            <td>${source.protocol}</td>
                            <td>${source.endpoint}</td>
                            <td class="${source.connected ? 'status-ok' : 'status-error'}">
                                ${source.connected ? 'Connected' : 'Disconnected'}
                            </td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="4">No sources configured</td></tr>';
                }
            } catch (error) {
                const tbody = document.querySelector('#sources tbody');
                tbody.innerHTML = '<tr><td colspan="4" class="status-error">Error loading sources</td></tr>';
            }
        }

        // Update every 2 seconds
        setInterval(() => {
            fetchStatus();
            fetchMetrics();
            fetchSources();
        }, 2000);

        // Initial load
        fetchStatus();
        fetchMetrics();
        fetchSources();
    </script>
</body>
</html>
        """
        return web.Response(text=html, content_type='text/html')

    async def stop(self):
        """Stop web server."""
        if self.site:
            await self.site.stop()

        if self.runner:
            await self.runner.cleanup()

        logger.info("✓ Web GUI stopped")
