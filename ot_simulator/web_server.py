"""Web server for OT Simulator control and monitoring.

Provides REST API and web interface for:
- Starting/stopping simulators
- Injecting faults
- Viewing sensor values
- Monitoring statistics
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from aiohttp import web

from ot_simulator.config_loader import SimulatorConfig
from ot_simulator.sensor_models import IndustryType, get_industry_sensors

logger = logging.getLogger("ot_simulator.web")


class SimulatorWebServer:
    """Web server for simulator control."""

    def __init__(self, config: SimulatorConfig):
        self.config = config
        self.app = web.Application()
        self.simulators: dict[str, Any] = {}
        self.simulator_tasks: dict[str, asyncio.Task] = {}

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_get("/api/health", self.handle_health)
        self.app.router.add_get("/api/config", self.handle_get_config)
        self.app.router.add_get("/api/sensors", self.handle_list_sensors)
        self.app.router.add_get("/api/simulators", self.handle_list_simulators)
        self.app.router.add_get("/api/stats", self.handle_get_stats)

        # Simulator control
        self.app.router.add_post("/api/simulators/{protocol}/start", self.handle_start_simulator)
        self.app.router.add_post("/api/simulators/{protocol}/stop", self.handle_stop_simulator)
        self.app.router.add_post("/api/fault/inject", self.handle_inject_fault)

        # Static files
        static_dir = Path(__file__).parent / "web" / "static"
        if static_dir.exists():
            self.app.router.add_static("/static/", path=static_dir, name="static")

    async def handle_index(self, request: web.Request) -> web.Response:
        """Serve index page."""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>OT Data Simulator</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0b1218;
            color: #e8e8e8;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #ff3621; margin-bottom: 10px; }
        h2 { color: #00a8e1; margin-top: 30px; margin-bottom: 15px; font-size: 18px; }
        .subtitle { color: #888; margin-bottom: 30px; }
        .card {
            background: #1b3139;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .protocol-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .protocol-card {
            background: #1b3139;
            border-radius: 8px;
            padding: 20px;
            border: 2px solid #2d4550;
        }
        .protocol-card.running { border-color: #00a8e1; }
        .protocol-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .protocol-name {
            font-size: 20px;
            font-weight: bold;
            color: #00a8e1;
        }
        .status-badge {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }
        .status-running { background: rgba(0,168,225,0.2); color: #00a8e1; }
        .status-stopped { background: rgba(255,54,33,0.2); color: #ff3621; }
        button {
            background: #00a8e1;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            margin-right: 10px;
        }
        button:hover { background: #0090c4; }
        button.danger { background: #ff3621; }
        button.danger:hover { background: #e02f1c; }
        button:disabled { background: #555; cursor: not-allowed; }
        .stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
        .stat { background: #0b1218; padding: 10px; border-radius: 4px; }
        .stat-label { font-size: 12px; color: #888; }
        .stat-value { font-size: 20px; font-weight: bold; color: #00a8e1; margin-top: 5px; }
        .sensor-list {
            max-height: 300px;
            overflow-y: auto;
            background: #0b1218;
            padding: 15px;
            border-radius: 4px;
            font-size: 13px;
        }
        .sensor-item {
            padding: 8px 0;
            border-bottom: 1px solid #2d4550;
        }
        .sensor-item:last-child { border-bottom: none; }
        .sensor-name { color: #00a8e1; font-weight: 500; }
        .sensor-details { color: #888; font-size: 12px; margin-top: 4px; }
        .loading { text-align: center; padding: 40px; color: #888; }
    </style>
</head>
<body>
    <div class="container">
        <h1>OT Data Simulator</h1>
        <div class="subtitle">Multi-Protocol Industrial Sensor Simulator</div>

        <div class="protocol-grid" id="protocols">
            <div class="loading">Loading simulators...</div>
        </div>

        <h2>Sensor Inventory</h2>
        <div class="card">
            <div id="sensors" class="sensor-list">
                <div class="loading">Loading sensors...</div>
            </div>
        </div>
    </div>

    <script>
        // Fetch and display simulator status
        async function loadSimulators() {
            try {
                const response = await fetch('/api/simulators');
                const data = await response.json();

                const container = document.getElementById('protocols');
                container.innerHTML = Object.entries(data.simulators).map(([name, info]) => `
                    <div class="protocol-card ${info.running ? 'running' : ''}">
                        <div class="protocol-header">
                            <div class="protocol-name">${name.toUpperCase()}</div>
                            <div class="status-badge ${info.running ? 'status-running' : 'status-stopped'}">
                                ${info.running ? 'RUNNING' : 'STOPPED'}
                            </div>
                        </div>
                        <div class="stats">
                            <div class="stat">
                                <div class="stat-label">Sensors</div>
                                <div class="stat-value">${info.sensor_count || 0}</div>
                            </div>
                            <div class="stat">
                                <div class="stat-label">Updates</div>
                                <div class="stat-value">${info.update_count || info.message_count || 0}</div>
                            </div>
                        </div>
                        <div style="margin-top: 15px;">
                            <button onclick="startSimulator('${name}')" ${info.running ? 'disabled' : ''}>
                                Start
                            </button>
                            <button class="danger" onclick="stopSimulator('${name}')" ${!info.running ? 'disabled' : ''}>
                                Stop
                            </button>
                        </div>
                    </div>
                `).join('');
            } catch (error) {
                console.error('Error loading simulators:', error);
            }
        }

        // Fetch and display sensors
        async function loadSensors() {
            try {
                const response = await fetch('/api/sensors');
                const data = await response.json();

                const container = document.getElementById('sensors');
                container.innerHTML = Object.entries(data.sensors).map(([industry, sensors]) => `
                    <div style="margin-bottom: 20px;">
                        <div style="font-weight: bold; color: #00a8e1; margin-bottom: 8px;">
                            ${industry.toUpperCase()} (${sensors.length} sensors)
                        </div>
                        ${sensors.map(s => `
                            <div class="sensor-item">
                                <div class="sensor-name">${s.name}</div>
                                <div class="sensor-details">
                                    ${s.min_value} - ${s.max_value} ${s.unit} [${s.type}]
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `).join('');
            } catch (error) {
                console.error('Error loading sensors:', error);
            }
        }

        // Start simulator
        async function startSimulator(protocol) {
            try {
                await fetch(`/api/simulators/${protocol}/start`, { method: 'POST' });
                setTimeout(loadSimulators, 1000);
            } catch (error) {
                console.error('Error starting simulator:', error);
            }
        }

        // Stop simulator
        async function stopSimulator(protocol) {
            try {
                await fetch(`/api/simulators/${protocol}/stop`, { method: 'POST' });
                setTimeout(loadSimulators, 1000);
            } catch (error) {
                console.error('Error stopping simulator:', error);
            }
        }

        // Initial load
        loadSimulators();
        loadSensors();

        // Refresh every 5 seconds
        setInterval(loadSimulators, 5000);
    </script>
</body>
</html>
        """
        return web.Response(text=html, content_type="text/html")

    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({"status": "ok"})

    async def handle_get_config(self, request: web.Request) -> web.Response:
        """Get current configuration."""
        config_dict = {
            "opcua": {
                "enabled": self.config.opcua.enabled,
                "endpoint": self.config.opcua.endpoint,
                "update_rate_hz": self.config.opcua.update_rate_hz,
            },
            "mqtt": {
                "enabled": self.config.mqtt.enabled,
                "broker": f"{self.config.mqtt.broker.host}:{self.config.mqtt.broker.port}",
                "publish_rate_hz": self.config.mqtt.publish_rate_hz,
            },
            "modbus": {
                "enabled": self.config.modbus.enabled,
                "tcp": f"{self.config.modbus.tcp.host}:{self.config.modbus.tcp.port}",
                "update_rate_hz": self.config.modbus.update_rate_hz,
            },
        }
        return web.json_response(config_dict)

    async def handle_list_sensors(self, request: web.Request) -> web.Response:
        """List all available sensors."""
        sensors_by_industry = {}

        for industry in IndustryType:
            sensors = get_industry_sensors(industry)
            sensors_by_industry[industry.value] = [
                {
                    "name": s.config.name,
                    "type": s.config.sensor_type.value,
                    "unit": s.config.unit,
                    "min_value": s.config.min_value,
                    "max_value": s.config.max_value,
                    "nominal_value": s.config.nominal_value,
                }
                for s in sensors
            ]

        return web.json_response({"sensors": sensors_by_industry})

    async def handle_list_simulators(self, request: web.Request) -> web.Response:
        """List all simulators and their status."""
        simulators_status = {}

        # Check each protocol
        for protocol in ["opcua", "mqtt", "modbus"]:
            if protocol in self.simulators:
                sim = self.simulators[protocol]
                try:
                    stats = sim.get_stats()
                    simulators_status[protocol] = {
                        "running": stats.get("running", False),
                        **stats,
                    }
                except Exception:
                    simulators_status[protocol] = {"running": False, "error": "Failed to get stats"}
            else:
                simulators_status[protocol] = {"running": False}

        return web.json_response({"simulators": simulators_status})

    async def handle_get_stats(self, request: web.Request) -> web.Response:
        """Get statistics from all simulators."""
        stats = {}
        for protocol, sim in self.simulators.items():
            try:
                stats[protocol] = sim.get_stats()
            except Exception as e:
                stats[protocol] = {"error": str(e)}

        return web.json_response(stats)

    async def handle_start_simulator(self, request: web.Request) -> web.Response:
        """Start a specific simulator."""
        protocol = request.match_info["protocol"]

        if protocol in self.simulator_tasks and not self.simulator_tasks[protocol].done():
            return web.json_response({"error": f"{protocol} already running"}, status=400)

        try:
            # Import and create simulator
            if protocol == "opcua":
                from ot_simulator.opcua_simulator import OPCUASimulator

                sim = OPCUASimulator(self.config.opcua)
                self.simulators[protocol] = sim
                task = asyncio.create_task(sim.start())
                self.simulator_tasks[protocol] = task

            elif protocol == "mqtt":
                from ot_simulator.mqtt_simulator import MQTTSimulator

                sim = MQTTSimulator(self.config.mqtt)
                self.simulators[protocol] = sim
                task = asyncio.create_task(sim.start())
                self.simulator_tasks[protocol] = task

            elif protocol == "modbus":
                from ot_simulator.modbus_simulator import ModbusSimulator

                sim = ModbusSimulator(self.config.modbus)
                self.simulators[protocol] = sim
                if self.config.modbus.tcp.enabled:
                    task = asyncio.create_task(sim.start_tcp())
                    self.simulator_tasks[f"{protocol}-tcp"] = task
                if self.config.modbus.rtu.enabled:
                    task = asyncio.create_task(sim.start_rtu())
                    self.simulator_tasks[f"{protocol}-rtu"] = task

            else:
                return web.json_response({"error": f"Unknown protocol: {protocol}"}, status=400)

            logger.info(f"{protocol.upper()} simulator started")
            return web.json_response({"status": "started", "protocol": protocol})

        except Exception as e:
            logger.error(f"Error starting {protocol} simulator: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_stop_simulator(self, request: web.Request) -> web.Response:
        """Stop a specific simulator."""
        protocol = request.match_info["protocol"]

        if protocol not in self.simulators:
            return web.json_response({"error": f"{protocol} not running"}, status=400)

        try:
            sim = self.simulators[protocol]
            await sim.stop()

            # Cancel task
            if protocol in self.simulator_tasks:
                task = self.simulator_tasks[protocol]
                if not task.done():
                    task.cancel()
                del self.simulator_tasks[protocol]

            del self.simulators[protocol]

            logger.info(f"{protocol.upper()} simulator stopped")
            return web.json_response({"status": "stopped", "protocol": protocol})

        except Exception as e:
            logger.error(f"Error stopping {protocol} simulator: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_inject_fault(self, request: web.Request) -> web.Response:
        """Inject a fault into a sensor."""
        try:
            data = await request.json()
            protocol = data.get("protocol")
            sensor_path = data.get("sensor_path")
            duration = float(data.get("duration", 10.0))

            if not protocol or not sensor_path:
                return web.json_response({"error": "protocol and sensor_path required"}, status=400)

            if protocol not in self.simulators:
                return web.json_response({"error": f"{protocol} not running"}, status=400)

            sim = self.simulators[protocol]
            sim.inject_fault(sensor_path, duration)

            return web.json_response(
                {
                    "status": "fault_injected",
                    "protocol": protocol,
                    "sensor_path": sensor_path,
                    "duration": duration,
                }
            )

        except Exception as e:
            logger.error(f"Error injecting fault: {e}")
            return web.json_response({"error": str(e)}, status=500)


def create_app(config: SimulatorConfig) -> web.Application:
    """Create web application."""
    server = SimulatorWebServer(config)
    return server.app


async def run_server(app: web.Application, host: str = "0.0.0.0", port: int = 8989):
    """Run web server."""
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host, port)
    await site.start()

    logger.info(f"Web server started on http://{host}:{port}")

    # Keep server running
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logger.info("Web server stopping...")
    finally:
        await runner.cleanup()
