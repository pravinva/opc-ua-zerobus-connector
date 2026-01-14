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
    <title>OT Data Simulator - Advanced Visualization</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0b1218;
            color: #e8e8e8;
            padding: 20px;
        }
        .container { max-width: 1600px; margin: 0 auto; }
        h1 { color: #ff3621; margin-bottom: 10px; }
        h2 { color: #00a8e1; margin-top: 30px; margin-bottom: 15px; font-size: 18px; }
        .subtitle { color: #888; margin-bottom: 30px; }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid #2d4550;
        }
        .tab {
            background: #1b3139;
            padding: 12px 24px;
            cursor: pointer;
            border-radius: 8px 8px 0 0;
            transition: all 0.2s;
        }
        .tab:hover { background: #2d4550; }
        .tab.active { background: #00a8e1; color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
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
            max-height: 400px;
            overflow-y: auto;
            background: #0b1218;
            padding: 15px;
            border-radius: 4px;
            font-size: 13px;
        }
        .sensor-item {
            padding: 8px;
            border-bottom: 1px solid #2d4550;
            cursor: pointer;
            transition: background 0.2s;
        }
        .sensor-item:hover { background: #1b3139; }
        .sensor-item.selected { background: #2d4550; border-left: 3px solid #00a8e1; }
        .sensor-item:last-child { border-bottom: none; }
        .sensor-name { color: #00a8e1; font-weight: 500; }
        .sensor-details { color: #888; font-size: 12px; margin-top: 4px; }
        .loading { text-align: center; padding: 40px; color: #888; }
        .chart-container {
            position: relative;
            height: 400px;
            background: #0b1218;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .chart-controls {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            align-items: center;
        }
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
        }
        .sensor-browser {
            display: grid;
            grid-template-columns: 250px 1fr;
            gap: 20px;
        }
        .correlation-value {
            font-size: 12px;
            color: #888;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>OT Data Simulator</h1>
        <div class="subtitle">Multi-Protocol Industrial Sensor Simulator with Advanced Visualization</div>

        <!-- Tab Navigation -->
        <div class="tabs">
            <div class="tab active" onclick="showTab('overview')">Overview</div>
            <div class="tab" onclick="showTab('visualization')">Live Visualization</div>
            <div class="tab" onclick="showTab('correlation')">Correlation Analysis</div>
            <div class="tab" onclick="showTab('health')">Equipment Health</div>
        </div>

        <!-- Overview Tab -->
        <div id="overview-tab" class="tab-content active">
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

        <!-- Visualization Tab -->
        <div id="visualization-tab" class="tab-content">
            <div class="card">
                <h2>Multi-Sensor Overlay</h2>
                <p style="color: #888; margin-bottom: 15px;">
                    Select multiple sensors (Ctrl+Click) from the list below, then create an overlay chart to compare them.
                </p>
                <div class="sensor-browser">
                    <div>
                        <h3 style="color: #00a8e1; margin-bottom: 10px;">Select Sensors</h3>
                        <div id="sensor-selector" class="sensor-list" style="max-height: 600px;">
                            <div class="loading">Loading sensors...</div>
                        </div>
                        <div class="chart-controls" style="margin-top: 15px;">
                            <button id="createOverlayBtn" onclick="createOverlayChart()" disabled>
                                Create Overlay Chart
                            </button>
                            <button onclick="clearSelection()">Clear</button>
                        </div>
                    </div>
                    <div>
                        <h3 style="color: #00a8e1; margin-bottom: 10px;">Live Charts</h3>
                        <div id="charts-container"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Correlation Tab -->
        <div id="correlation-tab" class="tab-content">
            <div class="card">
                <h2>Correlation Heatmap</h2>
                <p style="color: #888; margin-bottom: 15px;">
                    Analyze correlation between sensors for feature engineering and predictive maintenance.
                </p>
                <div class="chart-controls">
                    <label style="color: #888;">Industry:</label>
                    <select id="correlationIndustry" onchange="updateCorrelationHeatmap()">
                        <option value="mining">Mining</option>
                        <option value="utilities">Utilities</option>
                        <option value="manufacturing">Manufacturing</option>
                        <option value="oil_gas">Oil & Gas</option>
                    </select>
                    <button onclick="updateCorrelationHeatmap()">Refresh</button>
                </div>
                <div id="correlation-heatmap" style="height: 600px;"></div>
            </div>
        </div>

        <!-- Health Tab -->
        <div id="health-tab" class="tab-content">
            <div class="card">
                <h2>Equipment Health Dashboard</h2>
                <p style="color: #888; margin-bottom: 15px;">
                    Monitor equipment health metrics and remaining useful life (RUL).
                </p>
                <div class="charts-grid" id="health-dashboard">
                    <div class="loading">Loading health metrics...</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Global state
        const CHART_COLORS = ['#00a8e1', '#ff3621', '#10b981', '#fbbf24', '#f97316', '#8b5cf6', '#ec4899', '#06b6d4'];
        let selectedSensors = new Set();
        let allSensorsData = {};
        let activeCharts = new Map();
        let sensorDataBuffers = new Map(); // Store historical data for each sensor

        // Tab management
        function showTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(tabName + '-tab').classList.add('active');

            // Initialize tab-specific content
            if (tabName === 'visualization') {
                loadSensorSelector();
            } else if (tabName === 'correlation') {
                updateCorrelationHeatmap();
            } else if (tabName === 'health') {
                loadHealthDashboard();
            }
        }

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
                allSensorsData = data.sensors;

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

        // Load sensor selector for visualization
        async function loadSensorSelector() {
            try {
                const response = await fetch('/api/sensors');
                const data = await response.json();
                allSensorsData = data.sensors;

                const container = document.getElementById('sensor-selector');
                container.innerHTML = Object.entries(data.sensors).map(([industry, sensors]) => `
                    <div style="margin-bottom: 20px;">
                        <div style="font-weight: bold; color: #00a8e1; margin-bottom: 8px;">
                            ${industry.toUpperCase()} (${sensors.length} sensors)
                        </div>
                        ${sensors.map(s => `
                            <div class="sensor-item"
                                 data-sensor-key="${industry}/${s.name}"
                                 data-sensor-unit="${s.unit}"
                                 data-sensor-name="${s.name}"
                                 onclick="toggleSensorSelection(event, '${industry}/${s.name}', '${s.unit}', '${s.name}')">
                                <div class="sensor-name">${s.name}</div>
                                <div class="sensor-details">
                                    ${s.min_value} - ${s.max_value} ${s.unit} [${s.type}]
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `).join('');
            } catch (error) {
                console.error('Error loading sensor selector:', error);
            }
        }

        // Toggle sensor selection
        function toggleSensorSelection(event, sensorKey, unit, name) {
            const item = event.currentTarget;

            if (event.ctrlKey || event.metaKey) {
                // Multi-select mode
                if (selectedSensors.has(sensorKey)) {
                    selectedSensors.delete(sensorKey);
                    item.classList.remove('selected');
                } else {
                    selectedSensors.add(sensorKey);
                    item.classList.add('selected');
                }
            } else {
                // Single select mode
                document.querySelectorAll('#sensor-selector .sensor-item').forEach(i => i.classList.remove('selected'));
                selectedSensors.clear();
                selectedSensors.add(sensorKey);
                item.classList.add('selected');
            }

            // Update button state
            const btn = document.getElementById('createOverlayBtn');
            btn.disabled = selectedSensors.size === 0;
            btn.textContent = `Create Overlay Chart (${selectedSensors.size} sensor${selectedSensors.size !== 1 ? 's' : ''})`;
        }

        // Clear selection
        function clearSelection() {
            selectedSensors.clear();
            document.querySelectorAll('#sensor-selector .sensor-item').forEach(i => i.classList.remove('selected'));
            document.getElementById('createOverlayBtn').disabled = true;
            document.getElementById('createOverlayBtn').textContent = 'Create Overlay Chart';
        }

        // Create overlay chart with multiple sensors
        async function createOverlayChart() {
            if (selectedSensors.size === 0) return;

            const chartId = 'chart-' + Date.now();
            const sensorsArray = Array.from(selectedSensors);

            // Get sensor metadata
            const sensorMetadata = sensorsArray.map(key => {
                const [industry, name] = key.split('/');
                const sensor = allSensorsData[industry].find(s => s.name === name);
                return { key, ...sensor };
            });

            // Group by unit for Y-axis assignment
            const unitGroups = {};
            sensorMetadata.forEach(s => {
                if (!unitGroups[s.unit]) unitGroups[s.unit] = [];
                unitGroups[s.unit].push(s);
            });

            // Create chart container
            const container = document.getElementById('charts-container');
            const chartDiv = document.createElement('div');
            chartDiv.className = 'card';
            chartDiv.innerHTML = `
                <div class="chart-controls">
                    <h3 style="color: #00a8e1; flex: 1;">Multi-Sensor Overlay (${sensorsArray.length} sensors)</h3>
                    <button onclick="removeChart('${chartId}')">Remove</button>
                </div>
                <div class="chart-container">
                    <canvas id="${chartId}"></canvas>
                </div>
                <div id="${chartId}-correlation" class="correlation-value"></div>
            `;
            container.appendChild(chartDiv);

            // Create datasets
            const datasets = sensorMetadata.map((sensor, i) => ({
                label: sensor.name + ' (' + sensor.unit + ')',
                data: [],
                borderColor: CHART_COLORS[i % CHART_COLORS.length],
                backgroundColor: CHART_COLORS[i % CHART_COLORS.length] + '33',
                yAxisID: 'y' + Object.keys(unitGroups).indexOf(sensor.unit),
                tension: 0.3,
                pointRadius: 0,
                borderWidth: 2
            }));

            // Create Y-axes
            const scales = {
                x: {
                    type: 'time',
                    time: { unit: 'second' },
                    title: { display: true, text: 'Time', color: '#888' },
                    ticks: { color: '#888' },
                    grid: { color: '#2d4550' }
                }
            };

            Object.keys(unitGroups).forEach((unit, i) => {
                scales['y' + i] = {
                    type: 'linear',
                    position: i % 2 === 0 ? 'left' : 'right',
                    title: { display: true, text: unit, color: '#888' },
                    ticks: { color: '#888' },
                    grid: { drawOnChartArea: i === 0, color: '#2d4550' }
                };
            });

            // Create chart
            const ctx = document.getElementById(chartId).getContext('2d');
            const chart = new Chart(ctx, {
                type: 'line',
                data: { datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    scales,
                    plugins: {
                        legend: {
                            display: true,
                            labels: { color: '#e8e8e8' }
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false
                        }
                    },
                    interaction: {
                        mode: 'nearest',
                        axis: 'x',
                        intersect: false
                    }
                }
            });

            activeCharts.set(chartId, { chart, sensors: sensorsArray, metadata: sensorMetadata });

            // Initialize data buffers
            sensorsArray.forEach(key => {
                if (!sensorDataBuffers.has(key)) {
                    sensorDataBuffers.set(key, []);
                }
            });

            // Start simulated data updates (in production, connect to WebSocket)
            startChartUpdates(chartId);
        }

        // Start updating chart with simulated data
        function startChartUpdates(chartId) {
            const chartData = activeCharts.get(chartId);
            if (!chartData) return;

            const updateInterval = setInterval(() => {
                const now = Date.now();
                const chart = chartData.chart;

                // Generate simulated data for each sensor
                chartData.sensors.forEach((sensorKey, i) => {
                    const metadata = chartData.metadata[i];
                    const buffer = sensorDataBuffers.get(sensorKey);

                    // Simulate sensor value
                    const range = metadata.max_value - metadata.min_value;
                    const nominal = metadata.nominal_value || (metadata.min_value + range / 2);
                    const noise = (Math.random() - 0.5) * range * 0.1;
                    const value = nominal + noise;

                    // Add to buffer
                    buffer.push({ x: now, y: value });

                    // Keep last 100 points
                    if (buffer.length > 100) buffer.shift();

                    // Update chart dataset
                    chart.data.datasets[i].data = [...buffer];
                });

                chart.update('none'); // Update without animation

                // Update correlation display
                updateCorrelationDisplay(chartId);

            }, 500); // Update every 500ms

            // Store interval for cleanup
            chartData.updateInterval = updateInterval;
        }

        // Update correlation display
        function updateCorrelationDisplay(chartId) {
            const chartData = activeCharts.get(chartId);
            if (!chartData || chartData.sensors.length < 2) return;

            const correlations = [];
            const datasets = chartData.chart.data.datasets;

            for (let i = 0; i < datasets.length - 1; i++) {
                for (let j = i + 1; j < datasets.length; j++) {
                    const r = pearsonCorrelation(
                        datasets[i].data.map(d => d.y),
                        datasets[j].data.map(d => d.y)
                    );

                    if (!isNaN(r)) {
                        correlations.push({
                            pair: `${chartData.metadata[i].name} ↔ ${chartData.metadata[j].name}`,
                            correlation: r.toFixed(3)
                        });
                    }
                }
            }

            const corrDiv = document.getElementById(chartId + '-correlation');
            if (corrDiv && correlations.length > 0) {
                corrDiv.innerHTML = '<strong>Correlations:</strong> ' +
                    correlations.map(c => `${c.pair}: r=${c.correlation}`).join(' | ');
            }
        }

        // Pearson correlation coefficient
        function pearsonCorrelation(x, y) {
            const n = Math.min(x.length, y.length);
            if (n < 2) return 0;

            const xMean = x.slice(0, n).reduce((a, b) => a + b, 0) / n;
            const yMean = y.slice(0, n).reduce((a, b) => a + b, 0) / n;

            let num = 0, denX = 0, denY = 0;
            for (let i = 0; i < n; i++) {
                const dx = x[i] - xMean;
                const dy = y[i] - yMean;
                num += dx * dy;
                denX += dx * dx;
                denY += dy * dy;
            }

            return num / Math.sqrt(denX * denY);
        }

        // Remove chart
        function removeChart(chartId) {
            const chartData = activeCharts.get(chartId);
            if (chartData) {
                if (chartData.updateInterval) clearInterval(chartData.updateInterval);
                chartData.chart.destroy();
                activeCharts.delete(chartId);
            }
            document.getElementById(chartId).closest('.card').remove();
        }

        // Update correlation heatmap
        async function updateCorrelationHeatmap() {
            const industry = document.getElementById('correlationIndustry').value;
            if (!allSensorsData[industry]) return;

            const sensors = allSensorsData[industry];
            const n = Math.min(sensors.length, 20); // Limit to 20 sensors for readability
            const selectedSensors = sensors.slice(0, n);

            // Generate simulated correlation matrix
            const matrix = Array(n).fill(0).map(() => Array(n).fill(0));
            const labels = selectedSensors.map(s => s.name);

            for (let i = 0; i < n; i++) {
                for (let j = 0; j < n; j++) {
                    if (i === j) {
                        matrix[i][j] = 1.0;
                    } else {
                        // Simulate correlation based on sensor types
                        const s1 = selectedSensors[i];
                        const s2 = selectedSensors[j];
                        let baseCorr = Math.random() * 0.4 - 0.2; // Base random correlation

                        // Increase correlation for related sensor types
                        if (s1.type === s2.type) baseCorr += 0.3;
                        if (s1.unit === s2.unit) baseCorr += 0.2;

                        matrix[i][j] = Math.max(-1, Math.min(1, baseCorr));
                    }
                }
            }

            // Create Plotly heatmap
            const data = [{
                z: matrix,
                x: labels,
                y: labels,
                type: 'heatmap',
                colorscale: 'RdBu',
                zmid: 0,
                colorbar: {
                    title: 'Correlation',
                    titlefont: { color: '#e8e8e8' },
                    tickfont: { color: '#e8e8e8' }
                }
            }];

            const layout = {
                title: {
                    text: `Sensor Correlation Matrix - ${industry.toUpperCase()}`,
                    font: { color: '#e8e8e8' }
                },
                xaxis: {
                    tickangle: -45,
                    tickfont: { color: '#888', size: 10 }
                },
                yaxis: {
                    autorange: 'reversed',
                    tickfont: { color: '#888', size: 10 }
                },
                plot_bgcolor: '#0b1218',
                paper_bgcolor: '#1b3139',
                font: { color: '#e8e8e8' }
            };

            Plotly.newPlot('correlation-heatmap', data, layout, {responsive: true});
        }

        // Load health dashboard
        function loadHealthDashboard() {
            const container = document.getElementById('health-dashboard');

            // Simulated equipment health data
            const equipment = [
                { id: 'crusher_1', name: 'Crusher 1', health: 0.85, rul: 240 },
                { id: 'mill_1', name: 'Mill 1', health: 0.72, rul: 180 },
                { id: 'compressor_1', name: 'Compressor 1', health: 0.91, rul: 360 },
                { id: 'transformer_1', name: 'Transformer 1', health: 0.78, rul: 200 }
            ];

            container.innerHTML = equipment.map(eq => {
                const color = getHealthColor(eq.health);
                const status = eq.health > 0.8 ? 'GOOD' : eq.health > 0.5 ? 'FAIR' : 'POOR';

                return `
                    <div class="card">
                        <h3 style="color: #00a8e1; margin-bottom: 15px;">${eq.name}</h3>
                        <div style="text-align: center;">
                            <div style="width: 150px; height: 150px; margin: 0 auto; position: relative;">
                                <svg viewBox="0 0 100 100">
                                    <circle cx="50" cy="50" r="40" fill="none" stroke="#2d4550" stroke-width="8"/>
                                    <circle cx="50" cy="50" r="40" fill="none" stroke="${color}"
                                            stroke-width="8" stroke-dasharray="${eq.health * 251.2} 251.2"
                                            transform="rotate(-90 50 50)" stroke-linecap="round"/>
                                    <text x="50" y="55" text-anchor="middle" font-size="20" fill="${color}" font-weight="bold">
                                        ${(eq.health * 100).toFixed(0)}%
                                    </text>
                                </svg>
                            </div>
                            <div class="stats" style="margin-top: 20px;">
                                <div class="stat">
                                    <div class="stat-label">Status</div>
                                    <div class="stat-value" style="color: ${color}">${status}</div>
                                </div>
                                <div class="stat">
                                    <div class="stat-label">RUL (hours)</div>
                                    <div class="stat-value">${eq.rul}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Get health color based on score
        function getHealthColor(score) {
            if (score > 0.8) return '#10b981';
            if (score > 0.5) return '#fbbf24';
            if (score > 0.3) return '#f97316';
            return '#ff3621';
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
