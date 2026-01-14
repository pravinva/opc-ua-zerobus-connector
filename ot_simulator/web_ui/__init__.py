"""Web UI package for OT Simulator.

This package contains the modular web interface components.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aiohttp import web

from ot_simulator.web_ui.api_handlers import APIHandlers
from ot_simulator.web_ui.opcua_browser import OPCUABrowser
from ot_simulator.web_ui.wot_browser import handle_wot_browser
from ot_simulator.web_ui.templates import get_main_page_html

if TYPE_CHECKING:
    from ot_simulator.simulator_manager import SimulatorManager


class EnhancedWebUI:
    """Enhanced professional web UI with real-time visualization.

    This is the main entry point for the web UI, delegating to modular components.
    """

    def __init__(self, config: Any, simulator_manager: SimulatorManager):
        """Initialize enhanced web UI.

        Args:
            config: Simulator configuration
            simulator_manager: SimulatorManager instance
        """
        self.config = config
        self.manager = simulator_manager
        self.app = web.Application()

        # Initialize modular components
        self.api_handlers = APIHandlers(config, simulator_manager)
        self.opcua_browser = OPCUABrowser(config, simulator_manager)

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_get("/api/health", self.api_handlers.handle_health)
        self.app.router.add_get("/api/sensors", self.api_handlers.handle_list_sensors)
        self.app.router.add_get("/api/industries", self.api_handlers.handle_list_industries)
        self.app.router.add_get("/api/opcua/hierarchy", self.opcua_browser.handle_opcua_hierarchy)
        # OPC-UA Thing Description endpoint
        self.app.router.add_get("/api/opcua/thing-description", self.api_handlers.handle_opcua_thing_description)
        # W3C WoT Thing Description Browser
        self.app.router.add_get("/wot/browser", handle_wot_browser)
        # Zero-Bus configuration endpoints
        self.app.router.add_post("/api/zerobus/config/load", self.api_handlers.handle_zerobus_config_load)
        self.app.router.add_post("/api/zerobus/config", self.api_handlers.handle_zerobus_config_save)
        self.app.router.add_post("/api/zerobus/test", self.api_handlers.handle_zerobus_test)
        # Zero-Bus streaming endpoints
        self.app.router.add_post("/api/zerobus/start", self.api_handlers.handle_zerobus_start)
        self.app.router.add_post("/api/zerobus/stop", self.api_handlers.handle_zerobus_stop)
        self.app.router.add_get("/api/zerobus/status", self.api_handlers.handle_zerobus_status)

    async def handle_index(self, request: web.Request) -> web.Response:
        """Serve enhanced professional UI with real-time charts and NLP."""
        html = get_main_page_html()
        return web.Response(text=html, content_type="text/html")


__all__ = ["EnhancedWebUI"]
