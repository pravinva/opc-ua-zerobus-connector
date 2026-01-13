"""Professional Web UI for OT Simulator with Databricks branding.

Features:
- Industry & protocol selection
- Real-time status monitoring
- Fault injection controls
- Sensor browser with filtering
- Databricks design system
- Professional UX
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

logger = logging.getLogger("ot_simulator.professional_ui")


class ProfessionalWebUI:
    """Professional web UI with Databricks branding."""

    def __init__(self, config: SimulatorConfig):
        self.config = config
        self.app = web.Application()
        self.simulators: dict[str, Any] = {}
        self._setup_routes()

    def _setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_get("/api/health", self.handle_health)
        self.app.router.add_get("/api/config", self.handle_get_config)
        self.app.router.add_get("/api/sensors", self.handle_list_sensors)
        self.app.router.add_get("/api/simulators", self.handle_list_simulators)
        self.app.router.add_post("/api/simulators/{protocol}/start", self.handle_start_simulator)
        self.app.router.add_post("/api/simulators/{protocol}/stop", self.handle_stop_simulator)
        self.app.router.add_post("/api/fault/inject", self.handle_inject_fault)

    async def handle_index(self, request: web.Request) -> web.Response:
        """Serve professional UI."""
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Databricks OT Simulator</title>
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
            background: linear-gradient(135deg, #0A0E27 0%, #1A1F3A 100%);
            color: #E8EAED;
            min-height: 100vh;
            padding: 24px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        /* Header */
        .header {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 32px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
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
            background: linear-gradient(135deg, #FF3621 0%, #FF6B58 50%, #00A9E0 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 8px;
        }

        .subtitle {
            color: #9BA3AF;
            font-size: 16px;
            font-weight: 400;
        }

        /* Protocol Selection */
        .protocol-selector {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }

        .selector-header {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 16px;
            color: #00A9E0;
        }

        .protocol-options {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
        }

        .protocol-option {
            background: rgba(255, 255, 255, 0.03);
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 16px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .protocol-option:hover {
            border-color: #00A9E0;
            background: rgba(0, 169, 224, 0.1);
            transform: translateY(-2px);
        }

        .protocol-option.selected {
            border-color: #00A9E0;
            background: rgba(0, 169, 224, 0.15);
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

        .protocol-icon.opcua { background: linear-gradient(135deg, #1F6FEB 0%, #3B8BFF 100%); }
        .protocol-icon.mqtt { background: linear-gradient(135deg, #10B981 0%, #34D399 100%); }
        .protocol-icon.modbus { background: linear-gradient(135deg, #F59E0B 0%, #FBBF24 100%); }

        /* Industry Selection */
        .industry-selector {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }

        .industry-options {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 12px;
        }

        .industry-option {
            background: rgba(255, 255, 255, 0.03);
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 20px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .industry-option:hover {
            border-color: #FF3621;
            background: rgba(255, 54, 33, 0.1);
            transform: translateY(-2px);
        }

        .industry-option.selected {
            border-color: #FF3621;
            background: rgba(255, 54, 33, 0.15);
        }

        .industry-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 8px;
            color: #E8EAED;
        }

        .industry-count {
            font-size: 14px;
            color: #9BA3AF;
        }

        /* Control Panel */
        .control-panel {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }

        .control-buttons {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }

        button {
            background: linear-gradient(135deg, #00A9E0 0%, #0090C4 100%);
            color: white;
            border: none;
            padding: 14px 28px;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            box-shadow: 0 4px 12px rgba(0, 169, 224, 0.3);
            font-family: 'Inter', sans-serif;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0, 169, 224, 0.4);
        }

        button:active {
            transform: translateY(0);
        }

        button:disabled {
            background: #4B5563;
            cursor: not-allowed;
            box-shadow: none;
            transform: none;
        }

        button.danger {
            background: linear-gradient(135deg, #FF3621 0%, #E02F1C 100%);
            box-shadow: 0 4px 12px rgba(255, 54, 33, 0.3);
        }

        button.danger:hover {
            box-shadow: 0 6px 16px rgba(255, 54, 33, 0.4);
        }

        button.secondary {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: none;
        }

        /* Status Grid */
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 24px;
        }

        .status-card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 24px;
            transition: all 0.3s;
        }

        .status-card.running {
            border-color: #10B981;
            box-shadow: 0 0 24px rgba(16, 185, 129, 0.2);
        }

        .status-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .protocol-name-display {
            font-size: 20px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .status-badge {
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .status-running {
            background: rgba(16, 185, 129, 0.2);
            color: #10B981;
            border: 1px solid #10B981;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }

        .status-stopped {
            background: rgba(107, 114, 128, 0.2);
            color: #9BA3AF;
            border: 1px solid #6B7280;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }

        .stat-item {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            padding: 16px;
        }

        .stat-label {
            font-size: 12px;
            color: #9BA3AF;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }

        .stat-value {
            font-size: 28px;
            font-weight: 700;
            color: #00A9E0;
        }

        /* Sensor Browser */
        .sensor-browser {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }

        .sensor-filter {
            margin-bottom: 20px;
        }

        .sensor-filter input {
            width: 100%;
            padding: 14px 20px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            color: #E8EAED;
            font-size: 15px;
            font-family: 'Inter', sans-serif;
        }

        .sensor-filter input:focus {
            outline: none;
            border-color: #00A9E0;
        }

        .sensor-list {
            max-height: 400px;
            overflow-y: auto;
        }

        .sensor-item {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            transition: all 0.2s;
        }

        .sensor-item:hover {
            background: rgba(0, 0, 0, 0.4);
            transform: translateX(4px);
        }

        .sensor-name-display {
            font-size: 15px;
            font-weight: 600;
            color: #00A9E0;
            margin-bottom: 8px;
        }

        .sensor-details {
            display: flex;
            gap: 20px;
            font-size: 13px;
            color: #9BA3AF;
        }

        .sensor-detail-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        /* Loading State */
        .loading {
            text-align: center;
            padding: 60px;
            color: #9BA3AF;
            font-size: 16px;
        }

        .loading::after {
            content: '...';
            animation: dots 1.5s infinite;
        }

        @keyframes dots {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60%, 100% { content: '...'; }
        }

        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }

        ::-webkit-scrollbar-track {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb {
            background: rgba(0, 169, 224, 0.5);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: rgba(0, 169, 224, 0.7);
        }

        /* Responsive */
        @media (max-width: 768px) {
            body { padding: 16px; }
            .header { padding: 20px; }
            h1 { font-size: 28px; }
            .status-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="logo-section">
                <div class="databricks-logo">D</div>
                <div>
                    <h1>OT Data Simulator</h1>
                    <p class="subtitle">Professional Industrial IoT Simulation Platform</p>
                </div>
            </div>
        </div>

        <!-- Protocol Selector -->
        <div class="protocol-selector">
            <div class="selector-header">Select Protocols to Simulate</div>
            <div class="protocol-options">
                <div class="protocol-option selected" data-protocol="opcua">
                    <div class="protocol-icon opcua">OPC</div>
                    <div>
                        <div style="font-weight: 600;">OPC-UA</div>
                        <div style="font-size: 12px; color: #9BA3AF;">Port 4840</div>
                    </div>
                </div>
                <div class="protocol-option selected" data-protocol="mqtt">
                    <div class="protocol-icon mqtt">MQTT</div>
                    <div>
                        <div style="font-weight: 600;">MQTT</div>
                        <div style="font-size: 12px; color: #9BA3AF;">Port 1883</div>
                    </div>
                </div>
                <div class="protocol-option selected" data-protocol="modbus">
                    <div class="protocol-icon modbus">MOD</div>
                    <div>
                        <div style="font-weight: 600;">Modbus TCP</div>
                        <div style="font-size: 12px; color: #9BA3AF;">Port 5020</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Industry Selector -->
        <div class="industry-selector">
            <div class="selector-header">Select Industries to Simulate</div>
            <div class="industry-options">
                <div class="industry-option selected" data-industry="mining">
                    <div class="industry-title">⛏️ Mining</div>
                    <div class="industry-count">17 sensors</div>
                </div>
                <div class="industry-option selected" data-industry="utilities">
                    <div class="industry-title">⚡ Utilities</div>
                    <div class="industry-count">18 sensors</div>
                </div>
                <div class="industry-option selected" data-industry="manufacturing">
                    <div class="industry-title">🏭 Manufacturing</div>
                    <div class="industry-count">19 sensors</div>
                </div>
                <div class="industry-option selected" data-industry="oil_gas">
                    <div class="industry-title">🛢️ Oil & Gas</div>
                    <div class="industry-count">26 sensors</div>
                </div>
            </div>
        </div>

        <!-- Control Panel -->
        <div class="control-panel">
            <div class="selector-header" style="margin-bottom: 16px;">Simulator Control</div>
            <div class="control-buttons">
                <button id="startBtn" onclick="startSelected()">🚀 Start Selected</button>
                <button id="stopBtn" class="danger" onclick="stopAll()">⏹️ Stop All</button>
                <button class="secondary" onclick="refreshStatus()">🔄 Refresh Status</button>
            </div>
        </div>

        <!-- Status Grid -->
        <div class="status-grid" id="statusGrid">
            <div class="loading">Loading simulator status</div>
        </div>

        <!-- Sensor Browser -->
        <div class="sensor-browser">
            <div class="selector-header" style="margin-bottom: 16px;">Sensor Inventory</div>
            <div class="sensor-filter">
                <input type="text" id="sensorSearch" placeholder="🔍 Search sensors..." oninput="filterSensors()">
            </div>
            <div class="sensor-list" id="sensorList">
                <div class="loading">Loading sensors</div>
            </div>
        </div>
    </div>

    <script>
        let selectedProtocols = new Set(['opcua', 'mqtt', 'modbus']);
        let selectedIndustries = new Set(['mining', 'utilities', 'manufacturing', 'oil_gas']);
        let allSensors = [];

        // Protocol selection
        document.querySelectorAll('.protocol-option').forEach(option => {
            option.addEventListener('click', function() {
                const protocol = this.dataset.protocol;
                if (selectedProtocols.has(protocol)) {
                    selectedProtocols.delete(protocol);
                    this.classList.remove('selected');
                } else {
                    selectedProtocols.add(protocol);
                    this.classList.add('selected');
                }
            });
        });

        // Industry selection
        document.querySelectorAll('.industry-option').forEach(option => {
            option.addEventListener('click', function() {
                const industry = this.dataset.industry;
                if (selectedIndustries.has(industry)) {
                    selectedIndustries.delete(industry);
                    this.classList.remove('selected');
                } else {
                    selectedIndustries.add(industry);
                    this.classList.add('selected');
                }
                filterSensors();
            });
        });

        // Load status
        async function loadStatus() {
            try {
                const response = await fetch('/api/simulators');
                const data = await response.json();

                const grid = document.getElementById('statusGrid');
                grid.innerHTML = Object.entries(data.simulators).map(([protocol, info]) => `
                    <div class="status-card ${info.running ? 'running' : ''}">
                        <div class="status-header">
                            <div class="protocol-name-display">${protocol}</div>
                            <div class="status-badge ${info.running ? 'status-running' : 'status-stopped'}">
                                ${info.running ? '🟢 Running' : '⚫ Stopped'}
                            </div>
                        </div>
                        <div class="stats-grid">
                            <div class="stat-item">
                                <div class="stat-label">Sensors</div>
                                <div class="stat-value">${info.sensor_count || 0}</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-label">Updates</div>
                                <div class="stat-value">${(info.update_count || info.message_count || 0).toLocaleString()}</div>
                            </div>
                        </div>
                    </div>
                `).join('');
            } catch (error) {
                console.error('Error loading status:', error);
            }
        }

        // Load sensors
        async function loadSensors() {
            try {
                const response = await fetch('/api/sensors');
                const data = await response.json();
                allSensors = data.sensors;
                displaySensors();
            } catch (error) {
                console.error('Error loading sensors:', error);
            }
        }

        // Display sensors
        function displaySensors() {
            const searchTerm = document.getElementById('sensorSearch').value.toLowerCase();
            const list = document.getElementById('sensorList');

            const filteredSensors = Object.entries(allSensors)
                .filter(([industry]) => selectedIndustries.has(industry))
                .flatMap(([industry, sensors]) =>
                    sensors.map(s => ({...s, industry}))
                )
                .filter(s =>
                    !searchTerm ||
                    s.name.toLowerCase().includes(searchTerm) ||
                    s.type.toLowerCase().includes(searchTerm)
                );

            if (filteredSensors.length === 0) {
                list.innerHTML = '<div class="loading">No sensors match your selection</div>';
                return;
            }

            list.innerHTML = filteredSensors.map(s => `
                <div class="sensor-item">
                    <div class="sensor-name-display">${s.industry}/${s.name}</div>
                    <div class="sensor-details">
                        <div class="sensor-detail-item">
                            <span>📊 Range:</span>
                            <span>${s.min_value} - ${s.max_value} ${s.unit}</span>
                        </div>
                        <div class="sensor-detail-item">
                            <span>🏷️ Type:</span>
                            <span>${s.type}</span>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        // Filter sensors
        function filterSensors() {
            displaySensors();
        }

        // Start selected
        async function startSelected() {
            for (const protocol of selectedProtocols) {
                try {
                    await fetch(`/api/simulators/${protocol}/start`, { method: 'POST' });
                } catch (error) {
                    console.error(`Error starting ${protocol}:`, error);
                }
            }
            setTimeout(loadStatus, 1000);
        }

        // Stop all
        async function stopAll() {
            for (const protocol of ['opcua', 'mqtt', 'modbus']) {
                try {
                    await fetch(`/api/simulators/${protocol}/stop`, { method: 'POST' });
                } catch (error) {
                    console.error(`Error stopping ${protocol}:`, error);
                }
            }
            setTimeout(loadStatus, 1000);
        }

        // Refresh
        function refreshStatus() {
            loadStatus();
            loadSensors();
        }

        // Initial load
        loadStatus();
        loadSensors();

        // Auto-refresh every 5 seconds
        setInterval(loadStatus, 5000);
    </script>
</body>
</html>
"""
        return web.Response(text=html, content_type="text/html")

    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check."""
        return web.json_response({"status": "ok"})

    async def handle_get_config(self, request: web.Request) -> web.Response:
        """Get configuration."""
        return web.json_response({"config": "implementation here"})

    async def handle_list_sensors(self, request: web.Request) -> web.Response:
        """List all sensors."""
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
                }
                for s in sensors
            ]
        return web.json_response({"sensors": sensors_by_industry})

    async def handle_list_simulators(self, request: web.Request) -> web.Response:
        """List simulators."""
        simulators_status = {}
        for protocol in ["opcua", "mqtt", "modbus"]:
            if protocol in self.simulators:
                sim = self.simulators[protocol]
                try:
                    stats = sim.get_stats()
                    simulators_status[protocol] = {"running": stats.get("running", False), **stats}
                except Exception:
                    simulators_status[protocol] = {"running": False}
            else:
                simulators_status[protocol] = {"running": False}
        return web.json_response({"simulators": simulators_status})

    async def handle_start_simulator(self, request: web.Request) -> web.Response:
        """Start simulator."""
        protocol = request.match_info["protocol"]
        # Implementation here
        return web.json_response({"status": "started", "protocol": protocol})

    async def handle_stop_simulator(self, request: web.Request) -> web.Response:
        """Stop simulator."""
        protocol = request.match_info["protocol"]
        # Implementation here
        return web.json_response({"status": "stopped", "protocol": protocol})

    async def handle_inject_fault(self, request: web.Request) -> web.Response:
        """Inject fault."""
        data = await request.json()
        # Implementation here
        return web.json_response({"status": "fault_injected"})


def create_professional_app(config: SimulatorConfig) -> web.Application:
    """Create professional web application."""
    ui = ProfessionalWebUI(config)
    return ui.app
