"""WebSocket server for real-time sensor data streaming.

Provides bidirectional real-time communication for:
- Live sensor data streaming
- Natural language command processing
- Simulator status updates
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from aiohttp import web
import aiohttp

logger = logging.getLogger("ot_simulator.websocket")


class WebSocketServer:
    """WebSocket server for real-time data streaming."""

    def __init__(self, simulator_manager, llm_agent=None):
        """Initialize WebSocket server.

        Args:
            simulator_manager: Reference to simulator manager (holds all protocol simulators)
            llm_agent: Optional LLM agent for natural language processing
        """
        self.manager = simulator_manager
        self.llm_agent = llm_agent
        self.connections: set[web.WebSocketResponse] = set()
        self.subscriptions: dict[web.WebSocketResponse, set[str]] = {}
        self.broadcast_task = None
        self.update_interval = 0.5  # 500ms default

    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connection."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.connections.add(ws)
        logger.info(f"WebSocket connection established. Total connections: {len(self.connections)}")

        # Send initial status
        await self.send_status_update(ws)

        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self.handle_message(ws, data)
                    except json.JSONDecodeError:
                        await ws.send_json({"type": "error", "message": "Invalid JSON"})
                    except Exception as e:
                        logger.error(f"Error handling message: {e}", exc_info=True)
                        await ws.send_json({"type": "error", "message": str(e)})
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        finally:
            self.connections.discard(ws)
            if ws in self.subscriptions:
                del self.subscriptions[ws]
            logger.info(f"WebSocket connection closed. Total connections: {len(self.connections)}")

        return ws

    async def handle_message(self, ws: web.WebSocketResponse, data: dict[str, Any]):
        """Handle incoming WebSocket message.

        Args:
            ws: WebSocket connection
            data: Parsed JSON message
        """
        msg_type = data.get("type")

        if msg_type == "subscribe":
            # Subscribe to sensor data
            sensors = data.get("sensors", [])
            if ws not in self.subscriptions:
                self.subscriptions[ws] = set()
            self.subscriptions[ws].update(sensors)
            logger.info(f"Client subscribed to {len(sensors)} sensors")
            await ws.send_json({"type": "subscribed", "sensors": list(self.subscriptions[ws])})

        elif msg_type == "unsubscribe":
            # Unsubscribe from sensor data
            sensors = data.get("sensors", [])
            if ws in self.subscriptions:
                self.subscriptions[ws].difference_update(sensors)
            await ws.send_json({"type": "unsubscribed", "sensors": sensors})

        elif msg_type == "nlp_command":
            # Natural language command
            text = data.get("text", "")
            logger.info(f"Received NLP command: '{text}'")

            if not text:
                logger.warning("Empty NLP command text")
                await ws.send_json({"type": "error", "message": "Empty command text"})
                return

            if self.llm_agent:
                try:
                    logger.info(f"Processing NLP command with LLM: '{text}'")
                    # Process with LLM
                    conversation_history = data.get("history", [])
                    command = await self.llm_agent.parse_with_llm(text, conversation_history)
                    logger.info(f"LLM parsed command: action={command.action}, target={command.target}")

                    # Execute command
                    logger.info(f"Executing command: {command.action}")
                    result = await self.execute_command(command)
                    logger.info(f"Command execution result: success={result.get('success', True)}, message={result.get('message', '')[:100]}")

                    # Phase 2: Have LLM synthesize the backend response into natural language
                    # Skip synthesis for actions that return detailed formatted data
                    if command.action in ["chat", "list_sensors", "status"]:
                        # Use raw backend message or reasoning directly
                        if command.action == "chat":
                            final_message = command.reasoning
                        else:
                            final_message = result.get("message", "")
                    else:
                        # Synthesize for simple actions (start, stop, inject_fault)
                        try:
                            synthesized_response = await self.llm_agent.synthesize_response(
                                user_query=text,
                                command=command,
                                backend_result=result
                            )
                            final_message = synthesized_response
                        except Exception as synth_error:
                            logger.warning(f"LLM synthesis failed, using backend message: {synth_error}")
                            final_message = result.get("message", "")

                    # Send response
                    response_data = {
                        "type": "nlp_response",
                        "action": command.action,
                        "target": command.target,
                        "parameters": command.parameters,
                        "reasoning": command.reasoning,
                        "success": result.get("success", True),
                        "message": final_message,
                    }
                    logger.info(f"Sending NLP response: action={command.action}, success={response_data['success']}")

                    try:
                        await ws.send_json(response_data)
                        logger.info("✓ NLP response sent successfully via WebSocket")
                    except Exception as send_error:
                        logger.error(f"✗ Failed to send WebSocket response: {send_error}", exc_info=True)

                except Exception as e:
                    logger.error(f"Error processing NLP command: {e}", exc_info=True)
                    try:
                        await ws.send_json(
                            {
                                "type": "nlp_response",
                                "action": "chat",
                                "reasoning": f"Error processing command: {str(e)}",
                                "success": False,
                            }
                        )
                        logger.info("✓ Error response sent via WebSocket")
                    except Exception as send_error:
                        logger.error(f"✗ Failed to send error response: {send_error}", exc_info=True)
            else:
                logger.warning("LLM agent not available")
                await ws.send_json({"type": "error", "message": "Natural language processing not available"})

        elif msg_type == "get_status":
            # Get current simulator status
            await self.send_status_update(ws)

        elif msg_type == "set_update_rate":
            # Change update rate
            interval = data.get("interval", 0.5)
            self.update_interval = max(0.1, min(5.0, interval))  # Clamp between 100ms and 5s
            await ws.send_json({"type": "update_rate_changed", "interval": self.update_interval})

        else:
            await ws.send_json({"type": "error", "message": f"Unknown message type: {msg_type}"})

    async def execute_command(self, command) -> dict[str, Any]:
        """Execute a parsed command from LLM.

        Args:
            command: Command object from LLM agent

        Returns:
            Result dictionary with success status and message
        """
        try:
            if command.action == "start":
                # Start simulator
                protocol = command.target
                logger.info(f"Start command: protocol={protocol}, available={list(self.manager.simulators.keys())}")
                if protocol in self.manager.simulators:
                    logger.info(f"Starting {protocol} simulator...")
                    await self.manager.start_simulator(protocol)
                    logger.info(f"✓ {protocol} simulator started successfully")
                    return {"success": True, "message": f"{protocol.upper()} started"}
                else:
                    logger.warning(f"Unknown protocol: {protocol}")
                    return {"success": False, "message": f"Unknown protocol: {protocol}"}

            elif command.action == "stop":
                # Stop simulator
                protocol = command.target
                logger.info(f"Stop command: protocol={protocol}")
                if protocol in self.manager.simulators:
                    logger.info(f"Stopping {protocol} simulator...")
                    await self.manager.stop_simulator(protocol)
                    logger.info(f"✓ {protocol} simulator stopped successfully")
                    return {"success": True, "message": f"{protocol.upper()} stopped"}
                else:
                    logger.warning(f"Unknown protocol: {protocol}")
                    return {"success": False, "message": f"Unknown protocol: {protocol}"}

            elif command.action == "inject_fault":
                # Inject fault
                sensor_path = command.target
                duration = command.parameters.get("duration", 60) if command.parameters else 60
                await self.manager.inject_fault(sensor_path, duration)
                return {"success": True, "message": f"Fault injected for {duration}s"}

            elif command.action == "status":
                # Generate formatted status report
                lines = ["=== Simulator Status ===", ""]

                for proto, simulator in self.manager.simulators.items():
                    # Check if simulator is running
                    if hasattr(simulator, "_running"):
                        is_running = simulator._running
                    elif hasattr(simulator, "get_stats"):
                        stats = simulator.get_stats()
                        is_running = stats.get("running", False)
                    else:
                        is_running = False

                    status_icon = "🟢 RUNNING" if is_running else "🔴 STOPPED"
                    lines.append(f"{proto.upper()}: {status_icon}")

                    if is_running:
                        # Get sensor count
                        if hasattr(simulator, "simulators"):
                            sensor_count = len(simulator.simulators)
                        elif hasattr(simulator, "get_stats"):
                            stats = simulator.get_stats()
                            sensor_count = stats.get("sensor_count", 0)
                        else:
                            sensor_count = 0

                        lines.append(f"  Sensors: {sensor_count}")

                    lines.append("")

                return {"success": True, "message": "\n".join(lines)}

            elif command.action == "list_sensors":
                # Generate formatted sensor list
                from ot_simulator.sensor_models import IndustryType, get_industry_sensors

                industry = command.target or "all"

                if industry == "all":
                    industries = list(IndustryType)
                else:
                    try:
                        industries = [IndustryType(industry.lower())]
                    except ValueError:
                        return {"success": False, "message": f"Unknown industry: {industry}"}

                lines = []
                total_count = 0

                for ind in industries:
                    sensors = get_industry_sensors(ind)
                    lines.append(f"\n=== {ind.value.upper()} ({len(sensors)} sensors) ===")

                    for sim in sensors:
                        cfg = sim.config
                        lines.append(f"  {cfg.name}")
                        lines.append(f"    Range: {cfg.min_value} - {cfg.max_value} {cfg.unit}")
                        lines.append(f"    Type: {cfg.sensor_type.value}")

                    total_count += len(sensors)

                lines.insert(0, f"Total: {total_count} sensors\n")

                return {"success": True, "message": "\n".join(lines)}

            elif command.action == "wot_query":
                # WoT semantic query - filter Thing Description browser AND list matching sensors
                from ot_simulator.sensor_models import IndustryType, get_industry_sensors

                params = command.parameters or {}
                semantic_type = params.get("semantic_type")
                industry_filter = params.get("industry")
                unit_filter = params.get("unit")
                search_text = params.get("search_text", "").lower()

                # Collect all matching sensors
                matching_sensors = []

                # Determine which industries to search
                if industry_filter:
                    try:
                        industries = [IndustryType(industry_filter.lower())]
                    except ValueError:
                        industries = list(IndustryType)
                else:
                    industries = list(IndustryType)

                # Search through all sensors
                for ind in industries:
                    sensors = get_industry_sensors(ind)
                    for sim in sensors:
                        cfg = sim.config
                        sensor_name = cfg.name.lower()

                        # Apply filters
                        matches = True

                        # Search text filter (match sensor name)
                        if search_text and search_text not in sensor_name:
                            matches = False

                        # Unit filter
                        if unit_filter and unit_filter.lower() not in cfg.unit.lower():
                            matches = False

                        # Semantic type filter (would need semantic metadata in sensor config)
                        # For now, skip semantic_type filtering

                        if matches:
                            matching_sensors.append({
                                "path": f"{ind.value}/{cfg.name}",
                                "name": cfg.name,
                                "unit": cfg.unit,
                                "range": f"{cfg.min_value}-{cfg.max_value}",
                                "type": cfg.sensor_type.value,
                                "industry": ind.value
                            })

                # Build response message
                filters_applied = []
                if search_text:
                    filters_applied.append(f"search: '{search_text}'")
                if industry_filter:
                    filters_applied.append(f"industry: {industry_filter}")
                if unit_filter:
                    filters_applied.append(f"unit: {unit_filter}")
                if semantic_type:
                    filters_applied.append(f"semantic type: {semantic_type}")

                filters_str = ", ".join(filters_applied) if filters_applied else "no filters"

                if not matching_sensors:
                    message = f"No sensors found matching filters: {filters_str}"
                else:
                    lines = [f"Found {len(matching_sensors)} sensor(s) matching {filters_str}:\n"]

                    # Group by industry
                    by_industry = {}
                    for sensor in matching_sensors:
                        ind = sensor["industry"]
                        if ind not in by_industry:
                            by_industry[ind] = []
                        by_industry[ind].append(sensor)

                    for ind_name in sorted(by_industry.keys()):
                        sensors_list = by_industry[ind_name]
                        lines.append(f"\n{ind_name.upper()} ({len(sensors_list)} sensors):")
                        for sensor in sensors_list:
                            lines.append(f"  • {sensor['name']}")
                            lines.append(f"    Range: {sensor['range']} {sensor['unit']}")
                            lines.append(f"    Type: {sensor['type']}")

                    message = "\n".join(lines)

                return {
                    "success": True,
                    "message": message,
                    "wot_filters": params,  # Include for frontend to apply
                    "matching_sensors": matching_sensors  # Include sensor list
                }

            elif command.action == "explain_wot_concept":
                # Explain WoT/ontology concepts
                target = command.target or "general"
                context = command.parameters.get("context", "") if command.parameters else ""

                # Build educational response
                explanations = {
                    "saref": "SAREF (Smart Appliances Reference) is an ETSI standard ontology for IoT devices.\n\n"
                             "Key concepts:\n"
                             "• saref:TemperatureSensor - Measures temperature (50+ in this simulator)\n"
                             "• saref:PowerSensor - Measures electrical power (40+ sensors)\n"
                             "• saref:PressureSensor - Measures pressure (30+ sensors)\n\n"
                             "Benefits: Protocol-independent device descriptions, automatic discovery, semantic queries.",

                    "sosa": "SOSA/SSN (Semantic Sensor Network) is a W3C standard for sensor metadata.\n\n"
                            "Key concepts:\n"
                            "• sosa:Sensor - Generic sensor for observations\n"
                            "• sosa:observes - Links sensor to what it measures\n"
                            "• Used for: Vibration, speed, force sensors\n\n"
                            "Benefits: Richer context, observation patterns, sensor capabilities.",

                    "qudt": "QUDT (Quantities, Units, Dimensions, Types) provides standardized unit identifiers.\n\n"
                            "Examples:\n"
                            "• °C → http://qudt.org/vocab/unit/DEG_C\n"
                            "• kW → http://qudt.org/vocab/unit/KiloW\n"
                            "• bar → http://qudt.org/vocab/unit/BAR\n\n"
                            "Benefits: Automatic unit conversion, machine-readable, protocol-independent.",

                    "thing_description": "W3C WoT Thing Description (TD) is a JSON-LD document describing IoT devices.\n\n"
                                        "Structure:\n"
                                        "• @context: Ontology definitions\n"
                                        "• properties: 379 sensors with metadata\n"
                                        "• forms: Protocol bindings (OPC-UA, MQTT, Modbus)\n"
                                        "• security: Authentication methods\n\n"
                                        "This simulator's TD is at: /api/opcua/thing-description",

                    "semantic_type": "Semantic types classify sensors by WHAT they measure, not HOW.\n\n"
                                    "Example: crusher_1_motor_power and compressor_1_motor_power\n"
                                    "• Different industries (mining vs oil_gas)\n"
                                    "• Different protocols (OPC-UA vs MQTT)\n"
                                    "• Same semantic type: saref:PowerSensor\n\n"
                                    "Query: 'Show all power sensors' works across everything!",

                    "ontology": "An ontology is a formal way to represent knowledge about a domain.\n\n"
                               "For IoT:\n"
                               "• Defines sensor types (TemperatureSensor, PowerSensor)\n"
                               "• Defines relationships (sensor measures property)\n"
                               "• Enables semantic queries (find all temp sensors)\n\n"
                               "This simulator uses SAREF, SOSA, and QUDT ontologies."
                }

                explanation = explanations.get(target.lower(), command.reasoning)
                return {"success": True, "message": explanation}

            elif command.action == "recommend_sensors":
                # Recommend sensors for a use case
                params = command.parameters or {}
                use_case = params.get("use_case", "").lower()
                industry_filter = params.get("industry")

                recommendations = {
                    "equipment_health": {
                        "sensors": [
                            "mining/crusher_1_vibration_x (Bearing wear detection)",
                            "mining/crusher_1_vibration_y (Imbalance detection)",
                            "mining/crusher_1_bearing_temp (Overheating alert)",
                            "utilities/transformer_1_oil_temp (Thermal stress)",
                            "manufacturing/robot_1_joint_1_torque (Mechanical wear)"
                        ],
                        "explanation": "Equipment health monitoring focuses on:\n"
                                      "• Vibration (mechanical degradation)\n"
                                      "• Temperature (thermal stress)\n"
                                      "• Current/torque (electrical/mechanical load)"
                    },
                    "energy_monitoring": {
                        "sensors": [
                            "utilities/grid_main_frequency (Grid stability)",
                            "oil_gas/compressor_1_motor_power (High consumption: 300-900 kW)",
                            "mining/crusher_1_motor_power (200-800 kW range)",
                            "utilities/inverter_1_efficiency (Energy efficiency)",
                            "manufacturing/press_1_force (Process efficiency)"
                        ],
                        "explanation": "Energy monitoring focuses on:\n"
                                      "• Power sensors (consumption tracking)\n"
                                      "• Efficiency metrics (waste reduction)\n"
                                      "• Frequency (grid quality)"
                    },
                    "safety": {
                        "sensors": [
                            "oil_gas/h2s_detector_1_ppm (Toxic gas: alert > 10 ppm)",
                            "oil_gas/gas_detector_1_ppm (Combustible gas)",
                            "oil_gas/separator_1_pressure (Overpressure risk)",
                            "oil_gas/flare_temperature (Fire risk: 500-1500°C)",
                            "mining/dust_concentration (Air quality)"
                        ],
                        "explanation": "Safety monitoring focuses on:\n"
                                      "• Gas detection (toxic/combustible)\n"
                                      "• Pressure (explosion risk)\n"
                                      "• Temperature (fire risk)"
                    },
                    "predictive_maintenance": {
                        "sensors": [
                            "All vibration sensors (trend analysis)",
                            "All bearing_temp sensors (thermal trending)",
                            "All motor current sensors (electrical trending)",
                            "mining/mill_1_power (load pattern analysis)",
                            "utilities/transformer_1_load (capacity trending)"
                        ],
                        "explanation": "Predictive maintenance uses:\n"
                                      "• Historical trending\n"
                                      "• Pattern recognition\n"
                                      "• Anomaly detection\n"
                                      "• Degradation curves"
                    },
                    "process_optimization": {
                        "sensors": [
                            "oil_gas/pipeline_1_flow (Throughput optimization)",
                            "mining/ore_flow_rate (Material handling)",
                            "oil_gas/tank_1_level (Inventory management)",
                            "manufacturing/assembly_line_speed (Cycle time)",
                            "oil_gas/separator_1_level (Process efficiency)"
                        ],
                        "explanation": "Process optimization focuses on:\n"
                                      "• Flow rates (throughput)\n"
                                      "• Level sensors (inventory)\n"
                                      "• Speed sensors (cycle time)"
                    }
                }

                rec = recommendations.get(use_case)
                if rec:
                    sensor_list = "\n• ".join(rec["sensors"])
                    message = f"{rec['explanation']}\n\nRecommended sensors:\n• {sensor_list}\n\n" + command.reasoning
                else:
                    message = command.reasoning  # LLM's own recommendation

                return {"success": True, "message": message}

            elif command.action == "compare_sensors":
                # Comparative analysis of sensors
                params = command.parameters or {}
                dimension = params.get("dimension", "by_industry")

                if dimension == "by_industry":
                    message = (
                        "📊 Sensor Comparison by Industry:\n\n"
                        "Mining (16 sensors):\n"
                        "• Focus: Heavy equipment, material handling\n"
                        "• Key types: Power, vibration, flow, temperature\n"
                        "• Highlights: crusher_1_motor_power (200-800 kW)\n\n"
                        "Utilities (17 sensors):\n"
                        "• Focus: Power grid, transformers, renewable energy\n"
                        "• Key types: Power, voltage, current, efficiency\n"
                        "• Highlights: grid_main_frequency (59.5-60.5 Hz critical)\n\n"
                        "Manufacturing (18 sensors):\n"
                        "• Focus: Robotics, assembly, welding\n"
                        "• Key types: Torque, force, position, current\n"
                        "• Highlights: 6-axis robot with joint torque sensors\n\n"
                        "Oil & Gas (27 sensors - MOST DIVERSE):\n"
                        "• Focus: Pipelines, compression, safety\n"
                        "• Key types: Flow, pressure, temperature, gas detection\n"
                        "• Highlights: H2S detection (safety critical)"
                    )
                elif dimension == "by_semantic_type":
                    message = (
                        "🏷️ Sensor Comparison by Semantic Type:\n\n"
                        "saref:TemperatureSensor (50+ sensors):\n"
                        "• Most common type across all industries\n"
                        "• Range: 18°C (paint booth) to 1500°C (flare)\n"
                        "• Unit: All use °C with QUDT URIs\n\n"
                        "saref:PowerSensor (40+ sensors):\n"
                        "• Second most common\n"
                        "• Range: 5 kW (spindle) to 900 kW (compressor)\n"
                        "• Critical for energy monitoring\n\n"
                        "saref:PressureSensor (30+ sensors):\n"
                        "• Concentrated in oil_gas industry\n"
                        "• Units: bar, PSI (standardized via QUDT)\n"
                        "• Safety critical (overpressure risk)\n\n"
                        "sosa:Sensor (25+ sensors):\n"
                        "• Generic type for: vibration, speed, force\n"
                        "• Used when no specific SAREF type fits"
                    )
                elif dimension == "by_unit":
                    message = (
                        "📏 Sensor Comparison by Unit:\n\n"
                        "Temperature (°C): 50+ sensors\n"
                        "• QUDT URI: http://qudt.org/vocab/unit/DEG_C\n"
                        "• Range: -20°C to 1500°C\n\n"
                        "Power (kW/MW): 40+ sensors\n"
                        "• QUDT URIs: KiloW, MegaW\n"
                        "• Range: 5 kW to 900 kW\n\n"
                        "Pressure (bar/PSI): 30+ sensors\n"
                        "• QUDT URIs: BAR, PSI\n"
                        "• Critical for safety\n\n"
                        "Electrical (A/V): 25+ sensors\n"
                        "• QUDT URIs: A (ampere), V (volt)\n"
                        "• Power quality monitoring"
                    )
                else:
                    message = command.reasoning

                return {"success": True, "message": message}

            elif command.action == "chat":
                # Conversational response
                return {"success": True, "message": command.reasoning}

            else:
                return {"success": False, "message": f"Unknown action: {command.action}"}

        except Exception as e:
            logger.error(f"Error executing command: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    async def send_status_update(self, ws: web.WebSocketResponse):
        """Send current simulator status to WebSocket client."""
        status = {"type": "status_update", "timestamp": time.time(), "simulators": {}}

        for protocol, simulator in self.manager.simulators.items():
            # Use get_stats() if available, otherwise use _running flag
            if hasattr(simulator, "get_stats"):
                stats = simulator.get_stats()
                status["simulators"][protocol] = {
                    "running": stats.get("running", False),
                    "sensor_count": stats.get("sensor_count", 0),
                    "update_count": stats.get("update_count") or stats.get("message_count", 0),
                    "errors": stats.get("errors", 0),
                }
            else:
                # Fallback for simulators without get_stats()
                status["simulators"][protocol] = {
                    "running": getattr(simulator, "_running", False),
                    "sensor_count": len(simulator.simulators) if hasattr(simulator, "simulators") else 0,
                    "update_count": 0,
                    "errors": 0,
                }

        await ws.send_json(status)

    async def broadcast_sensor_data(self):
        """Periodically broadcast sensor data to subscribed clients."""
        logger.info("Starting sensor data broadcast task")

        while True:
            try:
                await asyncio.sleep(self.update_interval)

                if not self.connections:
                    continue

                # Collect all subscribed sensor paths
                all_sensors = set()
                for sensors in self.subscriptions.values():
                    all_sensors.update(sensors)

                if not all_sensors:
                    continue

                # Get current sensor values
                sensor_data = {}
                for sensor_path in all_sensors:
                    value = self.manager.get_sensor_value(sensor_path)
                    if value is not None:
                        sensor_data[sensor_path] = value

                if not sensor_data:
                    continue

                # Send to each subscribed client
                timestamp = time.time()
                disconnected = []

                for ws in list(self.connections):
                    if ws in self.subscriptions and self.subscriptions[ws]:
                        # Filter to only subscribed sensors for this client
                        client_data = {
                            sensor: value for sensor, value in sensor_data.items() if sensor in self.subscriptions[ws]
                        }

                        if client_data:
                            try:
                                await ws.send_json(
                                    {"type": "sensor_data", "timestamp": timestamp, "sensors": client_data}
                                )
                            except Exception as e:
                                logger.error(f"Error sending to client: {e}")
                                disconnected.append(ws)

                # Clean up disconnected clients
                for ws in disconnected:
                    self.connections.discard(ws)
                    if ws in self.subscriptions:
                        del self.subscriptions[ws]

            except asyncio.CancelledError:
                logger.info("Sensor data broadcast task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}", exc_info=True)
                await asyncio.sleep(1)  # Brief pause on error

    async def start_broadcast(self):
        """Start the broadcast task."""
        if self.broadcast_task is None:
            self.broadcast_task = asyncio.create_task(self.broadcast_sensor_data())

    async def stop_broadcast(self):
        """Stop the broadcast task."""
        if self.broadcast_task:
            self.broadcast_task.cancel()
            try:
                await self.broadcast_task
            except asyncio.CancelledError:
                pass
            self.broadcast_task = None

    async def broadcast_status_update(self):
        """Broadcast status update to all connected clients."""
        if not self.connections:
            return

        status = {"type": "status_update", "timestamp": time.time(), "simulators": {}}

        for protocol, simulator in self.manager.simulators.items():
            # Use get_stats() if available, otherwise use _running flag
            if hasattr(simulator, "get_stats"):
                stats = simulator.get_stats()
                status["simulators"][protocol] = {
                    "running": stats.get("running", False),
                    "sensor_count": stats.get("sensor_count", 0),
                    "update_count": stats.get("update_count") or stats.get("message_count", 0),
                    "errors": stats.get("errors", 0),
                }
            else:
                # Fallback for simulators without get_stats()
                status["simulators"][protocol] = {
                    "running": getattr(simulator, "_running", False),
                    "sensor_count": len(simulator.simulators) if hasattr(simulator, "simulators") else 0,
                    "update_count": 0,
                    "errors": 0,
                }

        for ws in list(self.connections):
            try:
                await ws.send_json(status)
            except Exception as e:
                logger.error(f"Error broadcasting status: {e}")
